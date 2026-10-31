"""Поиск техники с опечатками и в любой раскладке (wtpoligon/game/search.py) — примеры пользователя 26.10."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from wtpoligon.game import index as X  # noqa: E402
from wtpoligon.game import search as S  # noqa: E402


def v(name, ru, en='', kind='tank'):
    return {'name': name, 'ru': ru, 'en': en or ru, 'kind': kind, 'country': 'ussr', 'rank': 1, 'br': 1.0}


VEHICLES = [v('ussr_t_80bvm', 'Т-80БВМ'), v('ussr_t_80b', 'Т-80Б'), v('ussr_t_80', 'Т-80'),
            v('f_15c_golden_eagle', 'F-15C Golden Eagle', kind='air'), v('f_16c', 'F-16C', kind='air'),
            v('us_m1_abrams', 'M1 Abrams'), v('germ_pzkpfw_vi_ausf_h1_tiger', 'Tiger H1'),
            v('su_27', 'Су-27', 'Su-27', 'air')]


@unittest.skipIf(S.process is None, 'нет rapidfuzz')
class TestSearch(unittest.TestCase):
    def first(self, text):
        return X.search(VEHICLES, text)[0]['name']

    def test_user_examples(self):
        self.assertEqual(self.first('т80бмв'), 'ussr_t_80bvm')      # переставлены буквы
        self.assertEqual(self.first('т-80бвм'), 'ussr_t_80bvm')
        self.assertEqual(self.first('t80bvm'), 'ussr_t_80bvm')
        for q in ('f15c', 'ф15с', 'F-15C', 'ф-15ц'):
            self.assertEqual(self.first(q), 'f_15c_golden_eagle', q)
        self.assertEqual(self.first('абрамс'), 'us_m1_abrams')
        self.assertEqual(self.first('су 27'), 'su_27')
        self.assertEqual(self.first('тигр'), 'germ_pzkpfw_vi_ausf_h1_tiger')

    def test_no_false_hits(self):
        self.assertNotIn('f_16c', [x['name'] for x in X.search(VEHICLES, 'f15c')])
        self.assertEqual(X.search(VEHICLES, 'zzzzqqq'), [])

    def test_names_cleaned(self):
        self.assertEqual(X.clean_name('␙M1A1'), 'M1A1')
        self.assertEqual(X.clean_name('▄Tigre  HAD-E'), 'Tigre HAD-E')


if __name__ == '__main__':
    unittest.main()
