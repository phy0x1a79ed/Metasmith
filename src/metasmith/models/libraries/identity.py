from __future__ import annotations

import os
import stat as stat_mod
import time
import uuid
from pathlib import Path

from ...caching.keys import multihash_key, stat_multihash_key
from ...hashing import KeyGenerator
from ...logging import Log
from ..paths import is_deferred
from .pinned import _stamp

# A regular file this small is identified by its bytes; anything bigger, and any
# directory, by its stat. Reading a 24 GB reference or walking a tree on every
# load is the cost the stat avoids, and a small file is the case where reading is
# free and a reinstall or checkout that only moves the path and mtime must not
# move the id.
_DIGEST_MAX_BYTES = 1 << 20


def _by_content(st) -> bool:
    return stat_mod.S_ISREG(st.st_mode) and st.st_size <= _DIGEST_MAX_BYTES


def _forked(key: bytes, fork_id: str | None) -> str:
    if fork_id:
        key = multihash_key(key + b"\x00fork:" + fork_id.encode("utf-8"))
    return key.hex()


def _content_key(tag: bytes, path: Path, data: bytes) -> bytes:
    # `path` is the library path as given, which plays the row name: relative,
    # so the agent and the client derive the same id from their own copies, and
    # two rows holding the same bytes under different names stay distinct.
    return multihash_key(tag + b"\x00" + str(path).encode("utf-8") + b"\x00" + data)


def leaf_id(abs_path: Path, path: Path, fork_id: str | None = None) -> str | None:
    # The leaf identity of whatever is at `abs_path` on this host, or None if
    # this host cannot see it. The client mints with it and the agent
    # re-derives with it at staging (`workflow.leaf_identity`), so the two agree
    # wherever both can read the file.
    #
    # A stat id folds the absolute path on the filesystem being stat'd, so it is
    # meaningful only on the host that owns the file; a content id is the same
    # on every host holding the bytes.
    try:
        st = abs_path.stat()
        if _by_content(st):
            return _forked(_content_key(b"file", path, abs_path.read_bytes()), fork_id)
    except OSError:
        return None
    return _forked(stat_multihash_key(abs_path, st.st_mtime_ns), fork_id)


def value_leaf_id(abs_path: Path, path: Path, fork_id: str | None = None) -> str | None:
    # A value is its text whatever its size.
    try:
        data = abs_path.read_bytes()
    except OSError:
        return None
    return _forked(_content_key(b"value", path, data), fork_id)


def leaf_stamp(abs_path: Path) -> dict | None:
    # What a leaf looked like when its id was minted, kept beside the id so a
    # later load can tell a stat-identified leaf changed. Not part of the id.
    try:
        return _stamp(abs_path)
    except OSError:
        return None


class _LeafIdentity:
    def _leaf_id_of(self, path: Path) -> str | None:
        # A row spelled absolutely under this library is named by its relative
        # path, so the spelling does not move a content id.
        abs_path = self._abs(path)
        name = path
        if path.is_absolute():
            try:
                name = path.relative_to(self.location)
            except ValueError:
                pass
        return leaf_id(abs_path, name, self.fork_id)

    def _mint_leaf_id(self, path: Path, value: bool = False) -> str:
        key = stamp = None
        if value:
            key = value_leaf_id(self._abs(path), path, self.fork_id)
        elif is_deferred(path):
            key = multihash_key(b"deferred\x00" + str(path).encode("utf-8")).hex()
        elif not os.environ.get("METASMITH_LEAF_RANDOM"):
            key = self._leaf_id_of(path)
            stamp = leaf_stamp(self._abs(path)) if key is not None else None
        if key is None:
            raw = uuid.uuid4().bytes + time.time_ns().to_bytes(16, "big", signed=False)
            key = multihash_key(raw).hex()
        self.instance_meta[path] = {
            "instance_id": key,
            "origin": "leaf",
            "lineage_payload": None,
            "fork_id": self.fork_id,
            # This process invented the number. `Pack` does not carry the flag,
            # so a library that is saved and loaded again is a record rather
            # than a mint -- which is the whole difference the given path cares
            # about. See `plan._refuse_unminted_givens`.
            "minted": True,
        }
        if stamp is not None:
            self.instance_meta[path]["stamp"] = stamp
        if value:
            self.instance_meta[path]["value"] = True
        return self.instance_meta[path]["instance_id"]

    def _mark_value(self, path: Path) -> None:
        # A value item minted before values were hashed carries no flag, and an
        # edit is when it gets one.
        entry = self.instance_meta.get(path)
        if entry is not None and not entry.get("value"):
            entry["value"] = True
            entry.pop("stamp", None)

    def _remint_if_changed(self, path: Path, entry: dict) -> dict:
        # A leaf edited after its id was recorded gets a new one, or every step
        # that reads it is served the cache built from the old bytes. A recorded
        # id comes back unchanged while the file does, so existing caches hold.
        if entry.get("value"):
            entry["instance_id"] = value_leaf_id(self._abs(path), path, self.fork_id) \
                or entry["instance_id"]
            return entry
        if entry.get("origin", "leaf") != "leaf" or is_deferred(path) \
                or os.environ.get("METASMITH_LEAF_RANDOM"):
            return entry
        abs_path = self._abs(path)
        observed = leaf_stamp(abs_path)
        if observed is None:
            return entry
        if observed["kind"] == "file" and observed["size"] <= _DIGEST_MAX_BYTES:
            # Its bytes re-derive for the price of reading them, so the
            # recorded id is never trusted over them.
            fresh = self._leaf_id_of(path)
            if fresh is not None and fresh != entry["instance_id"]:
                Log.Info(f"[{abs_path}] is identified by its bytes, so its identity moved")
                entry["instance_id"] = fresh
            entry["stamp"] = observed
            return entry
        recorded = entry.get("stamp")
        if recorded is None:
            # An index written before stamps were. Its id is known to describe
            # these bytes only while it still re-derives from them.
            if self._leaf_id_of(path) == entry["instance_id"]:
                entry["stamp"] = observed
            return entry
        if recorded == observed:
            return entry
        old = entry["instance_id"]
        self._mint_leaf_id(path)
        fresh = self.instance_meta[path]
        fresh.pop("minted", None)
        if fresh["instance_id"] == old:
            # A new size under the same path and mtime, as `cp -p` leaves it.
            seed = f"{old}\x00changed:{sorted(observed.items())}".encode("utf-8")
            fresh["instance_id"] = multihash_key(seed).hex()
        Log.Info(f"[{abs_path}] changed since it was recorded, so its identity moved")
        return fresh

    def _refork_leaf_id(self, path: Path, entry: dict) -> dict:
        # A fork moves an identity the library already held, deliberately, to
        # get a new task key. Like an invalidate it acts on a record rather
        # than inventing one, so it clears the mint mark the given path reads.
        abs_path = self._abs(path)
        if entry.get("value") or (not os.environ.get("METASMITH_LEAF_RANDOM") and abs_path.exists()):
            self._mint_leaf_id(path, value=bool(entry.get("value")))
            self.instance_meta[path].pop("minted", None)
        else:
            seed = f"{entry['instance_id']}\x00fork:{self.fork_id}".encode("utf-8")
            self.instance_meta[path] = {
                "instance_id": multihash_key(seed).hex(),
                "origin": "leaf",
                "lineage_payload": None,
                "fork_id": self.fork_id,
            }
        return self.instance_meta[path]

    def _resolve_instance_meta(self, path: Path, dtype_name: str) -> dict:
        if self.is_pinned:
            entry = self.instance_meta.get(path)
            if entry is None:
                from .pinned import PinnedLibraryError
                raise PinnedLibraryError(
                    f"[{path}] is not recorded in the pinned library at"
                    f" [{self.location}], and a pinned library will not mint an"
                    " id. Rebuild and re-pin it."
                )
            return entry
        if path in self.instance_meta:
            entry = self.instance_meta[path]
            if entry.get("fork_id") == self.fork_id:
                return self._remint_if_changed(path, entry)
            if entry.get("origin", "leaf") != "leaf":
                entry["fork_id"] = self.fork_id
                return entry
            return self._refork_leaf_id(path, entry)
        _, legacy_id = KeyGenerator.FromStr("".join([
            str(path), dtype_name, self.GetKey(),
        ]), l=10)
        self.instance_meta[path] = {
            "instance_id": legacy_id,
            "origin": "leaf",
            "lineage_payload": None,
            "fork_id": self.fork_id,
            "minted": True,
        }
        return self.instance_meta[path]
