"""Перенос модификаций в копию (tools/wtlib/mods.py, docs/research/modifications.md)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from wtlib import blk as B  # noqa: E402
from wtlib import mods as M  # noqa: E402

UNIT = '''
commonWeapons{
  Weapon{
    trigger:t="gunner0"
  }
}
nightVision{
  driverIr{
    noiseFactor:r=0.2
  }
}
modifications{
  smoke{
    effects{
      commonWeapons{
        Weapon{
          trigger:t="gunner0"
        }
        Weapon{
          trigger:t="gunner4"
        }
      }
    }
  }
  nv{
    effects{
      nightVision{
        gunnerThermal{
          noiseFactor:r=0.04
        }
      }
    }
  }
  armor_kit{
    effects{
      hideNodes{
        node:t="armor_plate"
      }
    }
  }
  alt_gun_a{
    effects{
      commonWeapons{
        Weapon{
          trigger:t="alt_a"
        }
      }
    }
  }
  alt_gun_b{
    effects{
      commonWeapons{
        Weapon{
          trigger:t="alt_b"
        }
      }
    }
  }
  kit_1{
    effects{
      ammoStowages{
        stage:i=1
      }
    }
  }
  kit_2{
    effects{
      ammoStowages{
        stage:i=2
      }
    }
  }
  vent{
    effects{
      damagePartsOverride{
        part_a{}
      }
    }
  }
  wetting{
    effects{
      damagePartsOverride{
        part_b{}
      }
    }
  }
  engine_upg{}
  extinguisher{}
}
'''
GLOBAL = '''
armor_kit{
  invertEnableLogic:b=yes
}
smoke{
  group:t="smoke_mod"
}
alt_gun_a{
  group:t="guns"
}
alt_gun_b{
  group:t="guns"
}
kit_1{
  group:t="kits"
}
kit_2{
  group:t="kits"
  reqModification:t="kit_1"
}
engine_upg{
  invertEnableLogic:b=yes
  effects{
    mulHorsePowers:r=0.9
  }
}
extinguisher{
  effects{
    extinguisherActivationCount:i=2
  }
}
'''


def resolve(chosen=()):
    unit = B.parse_text(UNIT)
    log = []
    res = B.resolve_file('include "x"\n' + M.bake_text(unit, B.parse_text(GLOBAL), chosen), lambda p: unit, log)
    return res, log


class Classify(unittest.TestCase):
    def test_kinds(self):
        kinds = {r['name']: r['kind'] for r in M.classify(B.parse_text(UNIT), B.parse_text(GLOBAL))}
        # smoke в группе один → переносим; alt_gun_a/b — одна группа, один блок → альтернативы;
        # kit_2 требует kit_1 → ступени: kit_1 вытеснен
        self.assertEqual(kinds, {'smoke': 'block', 'nv': 'block', 'armor_kit': 'stock_penalty',
                                 'alt_gun_a': 'alternative', 'alt_gun_b': 'alternative',
                                 'kit_1': 'superseded', 'kit_2': 'block', 'vent': 'block', 'wetting': 'block',
                                 'engine_upg': 'stock_penalty', 'extinguisher': 'lost'})

    def test_lost_equipment(self):
        self.assertEqual(M.lost_equipment(B.parse_text(UNIT), B.parse_text(GLOBAL)), ['extinguisher'])


class Bake(unittest.TestCase):
    def test_replaces_stock_block_whole_and_named(self):
        res, log = resolve()
        self.assertEqual(log, [])
        self.assertEqual(sum(1 for b in res.blocks if b.name == 'commonWeapons'), 1)
        self.assertEqual([w.get('trigger') for w in res.block('commonWeapons').blocks], ['gunner0', 'gunner4'])
        self.assertIsNotNone(res.block('nightVision').block('gunnerThermal'))

    def test_invert_not_baked(self):
        res, _ = resolve()
        self.assertIsNone(res.block('hideNodes'))

    def test_group_only_when_chosen(self):
        res, _ = resolve()
        self.assertNotIn('alt_a', [w.get('trigger') for w in res.block('commonWeapons').blocks])
        res, _ = resolve(chosen=('alt_gun_a',))
        self.assertEqual([w.get('trigger') for w in res.block('commonWeapons').blocks], ['alt_a'])

    def test_chain_takes_top_stage(self):
        res, _ = resolve()
        self.assertEqual(res.block('ammoStowages').get('stage'), 2)

    def test_absent_blocks_merged(self):
        res, _ = resolve()
        self.assertEqual([b.name for b in res.block('damagePartsOverride').blocks], ['part_a', 'part_b'])


if __name__ == '__main__':
    unittest.main()
