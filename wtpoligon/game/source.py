"""Источник данных игры: установленная игра (*.vromfs.bin) или клон датамайна (gszabi99/War-Thunder-Datamine,
JSON *.blkx — для тестов и облака без игры). Один интерфейс для индекса, сборки и проверки.

Пути — как в игре: 'gameData/units/tankModels/ussr_t_80bvm.blk' (регистр не важен; префикс '#/develop/gameBase/'
из include допускается). Возвращаемые деревья кэшируются — не менять их на месте (копировать: blk._clone).
"""
import functools
import json
import os
import subprocess

from . import blk as B
from . import images as IMG
from .vromfs import Vromfs

_INCLUDE_ROOT = '#/develop/gameBase/'


def _norm(path):
    p = (path or '').replace('\\', '/')
    if p.startswith(_INCLUDE_ROOT):
        p = p[len(_INCLUDE_ROOT):]
    return p.lower()


class Source:
    kind = ''
    root = ''
    version = None

    def load(self, path):
        """Дерево BLK файла или None."""
        return self._load(_norm(path))

    def mission(self, path):
        """Штатная миссия из mis.vromfs или распакованного датамайна."""
        return None

    def loader(self):
        """load(путь) для blk.resolve_file: нет файла — FileNotFoundError."""
        def load(path):
            t = self.load(path)
            if t is None:
                raise FileNotFoundError(path)
            return t
        return load

    def exists(self, path):
        raise NotImplementedError

    def list_files(self, prefix):
        """Пути файлов aces (нижний регистр, как в архиве: 'gamedata/weapons/…blk'), начинающиеся с prefix."""
        raise NotImplementedError

    def config(self, name):
        """char.vromfs: config/<name>.blk (unittags, wpcost, modifications …) или None."""
        raise NotImplementedError

    def lang_csv(self, name):
        """lang.vromfs: lang/<name>.csv текстом или None."""
        raise NotImplementedError

    def atlas_file(self, path):
        """atlases.vromfs: файл интерфейса игры (иконки вооружения gameuiskin/<имя>.png) байтами или None."""
        raise NotImplementedError

    def signature(self):
        """Строка, меняющаяся при обновлении данных (для кэша индекса)."""
        raise NotImplementedError

    def describe(self):
        return '%s %s%s' % ('игра' if self.kind == 'game' else 'датамайн', self.root,
                            ' (версия %s)' % self.version if self.version else '')


class GameSource(Source):
    """Установленная игра: aces.vromfs.bin (gameData), char.vromfs.bin (config), lang.vromfs.bin (lang)."""
    kind = 'game'

    def __init__(self, game_dir):
        self.root = game_dir
        self._vfs = {}
        self.errors = {}
        self._atlas_tails = None
        self.version = self._vromfs('aces').header.version

    # где ещё бывают архивы, кроме корня папки игры (интерфейс — в ui/)
    SUBDIRS = ('', 'ui')

    def archive_path(self, name):
        """Путь архива <name>.vromfs.bin: корень игры, ui/, иначе поиск на 2 уровня вглубь; None — нет."""
        for sub in self.SUBDIRS:
            p = os.path.join(self.root, sub, name + '.vromfs.bin')
            if os.path.isfile(p):
                return p
        for dirpath, dirs, files in os.walk(self.root):
            if dirpath[len(self.root):].count(os.sep) >= 2:
                dirs[:] = []
            if name + '.vromfs.bin' in files:
                return os.path.join(dirpath, name + '.vromfs.bin')
        return None

    def _vromfs(self, name):
        if name not in self._vfs:
            path = self.archive_path(name)
            vf, err = None, None
            if path:
                try:
                    vf = Vromfs(path)
                except Exception as e:  # noqa: BLE001 — архив интерфейса не обязателен: без него нет картинок
                    if name == 'aces':
                        raise
                    err = '%s: %s' % (type(e).__name__, e)
            self._vfs[name] = (vf, B.BinaryReader.for_vromfs(vf) if vf else None)
            self.errors[name] = err or ('' if path else 'нет %s.vromfs.bin в %s' % (name, self.root))
        return self._vfs[name][0]

    def _parse(self, archive, path):
        vf = self._vromfs(archive)
        data = vf.get(path) if vf else None
        if data is None:
            return None
        return self._vfs[archive][1].parse(data) if B.is_binary(data) else B.parse_text(data.decode('utf-8-sig'))

    @functools.lru_cache(maxsize=128)
    def _load(self, path):
        return self._parse('aces', path)

    @functools.lru_cache(maxsize=32)
    def mission(self, path):
        return self._parse('mis', _norm(path))

    def exists(self, path):
        return self._vromfs('aces').get(_norm(path)) is not None

    def list_files(self, prefix):
        p = _norm(prefix)
        return sorted(n for n in (k.lower() for k in self._vromfs('aces').files) if n.startswith(p))

    @functools.lru_cache(maxsize=16)
    def config(self, name):
        return self._parse('char', 'config/%s.blk' % name)

    @functools.lru_cache(maxsize=32)
    def lang_csv(self, name):
        vf = self._vromfs('lang')
        data = vf.get('lang/%s.csv' % name) if vf else None
        return data.decode('utf-8-sig', 'replace') if data is not None else None

    def atlas_raw(self, path):
        """Файл ui/atlases.vromfs.bin как есть (байты) или None; путь — точный или по концу пути."""
        vf = self._vromfs('atlases')
        if vf is None:
            return None
        data = vf.get(path.lower())
        if data is None:            # путь внутри архива с другим началом — ищем по концу пути
            if self._atlas_tails is None:
                self._atlas_tails = {}
                for k in vf.files:
                    parts = k.lower().split('/')
                    self._atlas_tails.setdefault('/'.join(parts[-2:]), k)
            key = self._atlas_tails.get('/'.join(path.lower().split('/')[-2:]))
            data = vf.files.get(key) if key else None
        return data

    def atlas_file(self, path):
        """Картинка 'gameuiskin/<имя>.png' / 'units/<имя>.png': в игре это .avif, .svg или .ddsx — отдаём PNG
        (или SVG); причина неудачи — в errors['atlas']."""
        base = path.lower().rsplit('.', 1)[0]
        for ext in IMG.EXTS:
            data = self.atlas_raw(base + ext)
            if data is None:
                continue
            out, err = IMG.decode(data, ext, self.root)
            if out is not None:
                return out
            self.errors['atlas'] = '%s%s: %s' % (base, ext, err)
        return None

    def signature(self):
        parts = ['game', self.version or '']
        for name in ('aces', 'char', 'lang'):
            p = os.path.join(self.root, name + '.vromfs.bin')
            st = os.stat(p) if os.path.isfile(p) else None
            parts.append('%s:%s:%s' % (name, st.st_size if st else '-', int(st.st_mtime) if st else '-'))
        return '|'.join(parts)


class DatamineSource(Source):
    """Клон датамайна: <клон>/aces.vromfs.bin_u/<путь в нижнем регистре>x (JSON). Типы восстанавливаются по JSON
    (blk.from_blkx) — для записи в игру сверять по установленной игре."""
    kind = 'datamine'

    def __init__(self, dm_dir):
        if not os.path.isdir(os.path.join(dm_dir, 'aces.vromfs.bin_u')):
            raise FileNotFoundError('не клон датамайна (нет aces.vromfs.bin_u): ' + dm_dir)
        self.root = dm_dir
        self.version = self._read_version()

    def _read_version(self):
        for p in ('version', os.path.join('aces.vromfs.bin_u', 'version')):
            full = os.path.join(self.root, p)
            if os.path.isfile(full):
                with open(full, encoding='utf-8', errors='replace') as f:
                    return f.read().strip()[:40] or None
        return None

    def _json(self, *parts):
        p = os.path.join(self.root, *parts)
        if not os.path.isfile(p):
            return None
        with open(p, encoding='utf-8') as f:
            return B.from_blkx(json.load(f))

    @functools.lru_cache(maxsize=128)
    def _load(self, path):
        return self._json('aces.vromfs.bin_u', *(path + 'x').split('/'))

    @functools.lru_cache(maxsize=32)
    def mission(self, path):
        return self._json('mis.vromfs.bin_u', *(_norm(path) + 'x').split('/'))

    def exists(self, path):
        return os.path.isfile(os.path.join(self.root, 'aces.vromfs.bin_u', *(_norm(path) + 'x').split('/')))

    def list_files(self, prefix):
        p = _norm(prefix)
        base = os.path.join(self.root, 'aces.vromfs.bin_u')
        top = os.path.join(base, *p.rstrip('/').split('/')[:-1]) if '/' in p else base
        out = []
        for dirpath, _dirs, names in os.walk(top):
            rel = os.path.relpath(dirpath, base).replace(os.sep, '/')
            for n in names:
                if n.endswith('.blkx'):
                    path = ('' if rel == '.' else rel + '/') + n[:-1]
                    if path.startswith(p):
                        out.append(path)
        return sorted(out)

    @functools.lru_cache(maxsize=16)
    def config(self, name):
        return self._json('char.vromfs.bin_u', 'config', name + '.blkx')

    @functools.lru_cache(maxsize=32)
    def lang_csv(self, name):
        p = os.path.join(self.root, 'lang.vromfs.bin_u', 'lang', name + '.csv')
        if not os.path.isfile(p):
            return None
        with open(p, encoding='utf-8-sig', errors='replace') as f:
            return f.read()

    def atlas_file(self, path):
        p = os.path.join(self.root, 'atlases.vromfs.bin_u', *path.lower().split('/'))
        if not os.path.isfile(p):
            return None
        with open(p, 'rb') as f:
            return f.read()

    def signature(self):
        head = ''
        try:
            head = subprocess.run(['git', '-C', self.root, 'rev-parse', 'HEAD'], capture_output=True, text=True,
                                  timeout=20).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        tags = os.path.join(self.root, 'char.vromfs.bin_u', 'config', 'unittags.blkx')
        mtime = int(os.stat(tags).st_mtime) if os.path.isfile(tags) else '-'
        return 'datamine|%s|%s|%s' % (os.path.abspath(self.root), head, mtime)


def open_source(game_dir=None, datamine=None):
    if datamine:
        return DatamineSource(datamine)
    if not game_dir:
        raise FileNotFoundError('папка игры не задана')
    if not os.path.isfile(os.path.join(game_dir, 'aces.vromfs.bin')):
        raise FileNotFoundError('нет aces.vromfs.bin в ' + game_dir)
    return GameSource(game_dir)
