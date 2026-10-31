"""Расшифровка логов War Thunder (.game_logs/*.clog).

Формат (установлено 24.10.2026, см. docs/research/tools.md): весь файл — открытый текст,
поXORенный повторяющимся ключом длиной 768 байт. Ключ одинаков для всех логов клиента.
Ключ не хранится в коде: он восстанавливается из самого лога — в каждом столбце (позиция mod 768)
самый частый байт открытого текста — пробел.
"""
import collections
import glob
import os
import sys

KEY_LEN = 768
_SAMPLE = 3_000_000


def derive_key(data: bytes) -> bytes:
    data = data[:_SAMPLE]
    return bytes(collections.Counter(data[c::KEY_LEN]).most_common(1)[0][0] ^ 0x20
                 for c in range(KEY_LEN))


def decrypt(data: bytes, key: bytes) -> bytes:
    k = (key * (len(data) // KEY_LEN + 1))[:len(data)]
    return (int.from_bytes(data, 'little') ^ int.from_bytes(k, 'little')).to_bytes(len(data), 'little')


def is_plausible(text: bytes) -> bool:
    """Доля управляющих символов (кроме \\t\\n\\r) в открытом тексте < 0.1%."""
    bad = sum(1 for b in text[:200_000] if b < 9 or 13 < b < 32 or b in (11, 12))
    return bad <= len(text[:200_000]) * 0.001


def key_for_dir(logs_dir: str) -> bytes:
    """Ключ из самого большого лога папки (в маленьких логах статистики мало)."""
    files = sorted(glob.glob(os.path.join(logs_dir, '*.clog')), key=os.path.getsize, reverse=True)
    if not files:
        raise FileNotFoundError('нет .clog в ' + logs_dir)
    with open(files[0], 'rb') as f:
        key = derive_key(f.read(_SAMPLE))
    with open(files[0], 'rb') as f:
        if not is_plausible(decrypt(f.read(200_000), key)):
            raise ValueError('ключ не подошёл: формат .clog изменился?')
    return key


def decrypt_dir(logs_dir: str, out_dir: str) -> list:
    """Расшифровывает все логи в out_dir/<имя>.log, пропуская уже расшифрованные."""
    key = key_for_dir(logs_dir)
    os.makedirs(out_dir, exist_ok=True)
    done = []
    for path in sorted(glob.glob(os.path.join(logs_dir, '*.clog'))):
        dst = os.path.join(out_dir, os.path.basename(path)[:-5] + '.log')
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(path):
            done.append((dst, True))
            continue
        with open(path, 'rb') as f:
            text = decrypt(f.read(), key)
        with open(dst, 'wb') as f:
            f.write(text)
        done.append((dst, is_plausible(text)))
    return done


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.expandvars(r'%LOCALAPPDATA%\WarThunder\.game_logs')
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'logs')
    res = decrypt_dir(src, dst)
    bad = [p for p, ok in res if not ok]
    print('расшифровано: %d, подозрительных: %d' % (len(res), len(bad)))
    for p in bad:
        print('  ', p)
