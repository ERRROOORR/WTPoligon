"""Сверка своего распаковщика VROMFS с wt_ext_cli (Raw): побайтно, по всем файлам всех архивов.

Подготовка эталона:
  tools\\ext\\wt_ext_cli.exe unpack_vromf -i <игра>\\<имя>.vromfs.bin -o cache\\ext_Raw --format Raw
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from wtlib.vromfs import Vromfs  # noqa: E402

GAME = os.path.expandvars(r'%LOCALAPPDATA%\WarThunder')
ARCHIVES = 'aces char game gui lang mis webUi wwdata'.split()


def ref_files(root):
    out = {}
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            out[os.path.relpath(p, root).replace(os.sep, '/')] = p
    return out


def main():
    total_bad = 0
    for v in ARCHIVES:
        vf = Vromfs(os.path.join(GAME, v + '.vromfs.bin'))
        ref = ref_files(os.path.join('cache', 'ext_Raw', v + '.vromfs.bin_u'))
        same, bad = 0, []
        for n, b in vf.files.items():
            k = n.lstrip('/')
            if k.startswith('\xff?'):
                k = k[2:]
            p = ref.pop(k, None)
            if p is None:
                bad.append('нет в эталоне: ' + n)
            elif open(p, 'rb').read() != b:
                bad.append('отличается: ' + n)
            else:
                same += 1
        extra = [k for k in ref if k != 'nm.txt']
        bad += ['нет у нас: ' + k for k in extra]
        total_bad += len(bad)
        print('%-7s %s pack=0x%02x ver=%s файлов=%d совпало=%d проблем=%d'
              % (v, vf.header.magic.decode(), vf.header.pack_type, vf.header.version, len(vf.files), same, len(bad)))
        for s in bad[:5]:
            print('    ', s)
    print('ИТОГО проблем:', total_bad)
    return 1 if total_bad else 0


if __name__ == '__main__':
    sys.exit(main())
