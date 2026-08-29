from __future__ import annotations

import asyncio
import importlib
import logging
import threading
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, SkipValidation, field_validator

from ._lazy import lazy_np, lazy_xr

ChunkIndex = tuple[int, ...]
LogType = logging.Logger


class Tracks(BaseModel):
    """
    Value Object de domínio para trajetórias de satélites.

    Encapsula um xarray.Dataset contendo posições (x, y, z) de múltiplos
    satélites ao longo do tempo, com metadados e validações.

    Attributes:
        dataset (Any): xarray.Dataset com as trajetórias.
            Dimensões: satellite, time, xyz
            Variáveis: positions, names, constellation
        satellite_names (list[str]): Lista de nomes dos satélites.
        time_range (tuple[str, str]): Intervalo temporal (início, fim).
        lock (threading.Lock): Lock para acesso thread-safe.
        async_lock (asyncio.Lock): Lock para acesso assíncrono.
        log (LogType): Logger para mensagens de debug.

    Notes:
        Esta classe valida a estrutura do dataset na inicialização,
        garantindo consistência dos dados.
    """

    dataset: Any
    satellite_names: list[str]
    time_range: tuple[str, str]

    lock: SkipValidation[threading.Lock] = Field(default_factory=threading.Lock, exclude=True)
    async_lock: SkipValidation[asyncio.Lock] = Field(default_factory=asyncio.Lock, exclude=True)
    log: SkipValidation[LogType] = Field(
        default_factory=lambda: logging.getLogger("tracks"), exclude=True
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    # ==========================================================
    # Validation
    # ==========================================================
    @field_validator("dataset")
    @classmethod
    def _validate_dataset(cls, ds):
        xr = lazy_xr()
        if not isinstance(ds, xr.Dataset):
            msg = "dataset deve ser xr.Dataset"
            raise TypeError(msg)

        cls._validate_structure(ds)
        cls._validate_positions_shape(ds)
        cls._validate_xyz_coords(ds)
        return ds

    @staticmethod
    def _validate_structure(ds) -> None:
        required_dims = {"satellite", "time", "xyz"}
        required_vars = {"positions", "names", "constellation"}

        if not required_dims.issubset(ds.sizes):
            msg = f"Dimensões ausentes: {required_dims - set(ds.sizes)}"
            raise ValueError(msg)

        all_vars = set(ds.data_vars) | set(ds.coords)
        if not required_vars.issubset(all_vars):
            msg = f"Variáveis ausentes: {required_vars - all_vars}"
            raise ValueError(msg)

    @staticmethod
    def _validate_positions_shape(ds) -> None:
        expected = (ds.sizes["satellite"], ds.sizes["time"], ds.sizes["xyz"])
        if ds["positions"].shape != expected:
            msg = f"'positions' deve ter shape {expected}"
            raise ValueError(msg)

    @staticmethod
    def _validate_xyz_coords(ds) -> None:
        try:
            if list(map(str, ds["xyz"].values)) != ["x", "y", "z"]:
                logging.getLogger("tracks").debug("Coord xyz fora do padrão")
        except Exception:
            pass

    # ==========================================================
    # Constructors
    # ==========================================================
    @classmethod
    def from_xr(cls, ds) -> Tracks:
        names = cls._extract_names(ds)
        t0, t1 = cls._extract_time_range(ds)
        return cls(dataset=ds, satellite_names=names, time_range=(t0, t1))

    # ==========================================================
    # Static helpers
    # ==========================================================
    @staticmethod
    def _extract_names(ds) -> list[str]:
        np = lazy_np()
        if "names" in ds:
            arr = ds["names"].astype(str)
            if hasattr(arr.data, "chunks"):
                return list(arr.compute().tolist())
            return list(np.asarray(arr).tolist())
        return [str(x) for x in ds["satellite"].values]

    @staticmethod
    def _extract_time_range(ds) -> tuple[str, str]:
        np = lazy_np()
        try:
            return str(ds.time.values[0]), str(ds.time.values[-1])
        except Exception:
            t = np.asarray(ds.time.values)
            return str(t[0]), str(t[-1])

    # ==========================================================
    # Filters
    # ==========================================================
    def _spawn(self, ds) -> Tracks:
        return Tracks.from_xr(ds)

    def filter_by_satellite(self, sat_id: int | tuple[int, ...]) -> Tracks:
        if isinstance(sat_id, int):
            sat_id = (sat_id,)
        return self._spawn(self.dataset.sel(satellite=list(sat_id)))

    def filter_by_constellation(self, const: str | tuple[str, ...]) -> Tracks:
        if isinstance(const, str):
            const = (const,)
        mask = self.dataset["constellation"].isin(const)
        return self._spawn(self.dataset.sel(satellite=mask))

    def filter_by_time(self, start=None, end=None) -> Tracks:
        ds = self.dataset
        if start is not None:
            ds = ds.sel(time=slice(start, None))
        if end is not None:
            ds = ds.sel(time=slice(None, end))
        return self._spawn(ds)

    # ==========================================================
    # Export
    # ==========================================================
    def to_zarr(
        self,
        path: str,
        *,
        mode="w",
        consolidated=True,
        zarr_format: int | None = 2,
        **kwargs,
    ) -> None:
        """Persiste o dataset em Zarr.

        ``zarr_format`` default é ``2`` (formato mais portável): o Zarr v3
        codifica coordenadas string (ex.: ``satellite``) como
        ``StringDType``/``vlen-utf8`` — fora da especificação v3, gerando
        warnings e dados menos interoperáveis.
        """
        with self.lock:
            self.dataset.to_zarr(path, mode=mode, zarr_format=zarr_format, **kwargs)
            if consolidated:
                try:
                    zarr = importlib.import_module("zarr")
                    zarr.consolidate_metadata(path)
                except Exception:
                    self.log.debug("Falha ao consolidar Zarr", exc_info=True)

    def to_hdf5(self, path: str, *, mode="w", engine="h5netcdf", **kwargs) -> None:
        with self.lock:
            self.dataset.to_netcdf(path, mode=mode, engine=engine, **kwargs)

    # ==========================================================
    # Chunk utilities
    # ==========================================================
    def get_chunks_info(self, var_name: str) -> dict[str, Any]:
        """Retorna informações sobre os chunks de uma variável do dataset.

        Args:
            var_name: Nome da variável (ex: "positions").

        Returns:
            dict com chaves 'chunks' (tupla de chunks ou None) e
            'num_chunk_grid' (número de chunks por dimensão ou (1,1,1)).
        """
        data = self.dataset[var_name].data
        # Tenta acessar chunks de diferentes tipos de array (dask, zarr, numpy)
        chunks = getattr(data, "chunks", None)
        if chunks is not None:
            numchunks = getattr(data, "numchunks", tuple(len(c) for c in chunks))
            return {"chunks": chunks, "num_chunk_grid": numchunks}
        return {"chunks": None, "num_chunk_grid": (1, 1, 1)}

    def get_chunks(
        self,
        var_name: str,
        max_chunks: int | None = None,
        max_total_bytes: int | None = None,
    ) -> dict[ChunkIndex, np.ndarray]:
        """Retorna chunks de uma variável como dict de arrays.

        Para datasets com chunks (dask), itera sobre os blocos.
        Para datasets sem chunks (numpy), retorna o array completo.

        Args:
            var_name: Nome da variável.
            max_chunks: Máximo de chunks a retornar.
            max_total_bytes: Limite de memória total (bytes).

        Returns:
            dict[tuple, np.ndarray]: Mapeia índice do chunk → array.
        """
        np = lazy_np()
        var = self.dataset[var_name]
        data = var.data

        # Tenta detectar se o array tem chunks (dask)
        chunks = getattr(data, "chunks", None)

        if chunks is not None:
            # Tenta vários métodos de iteração de chunks
            delayed_blocks = getattr(data, "to_delayed", None)
            if delayed_blocks is None:
                # Para arrays que não expõem to_delayed, computa chunks manualmente
                full = np.asarray(data)
                chunk_sizes = tuple(c[0] for c in chunks)
                result: dict[ChunkIndex, np.ndarray] = {}
                total_bytes = 0
                slices_per_dim = [range(0, full.shape[d], chunk_sizes[d]) for d in range(full.ndim)]
                import itertools

                for idx_flat, start_indices in enumerate(itertools.product(*slices_per_dim)):
                    if max_chunks is not None and len(result) >= max_chunks:
                        break
                    sl = tuple(slice(s, s + chunk_sizes[d]) for d, s in enumerate(start_indices))
                    block = np.asarray(full[sl])
                    total_bytes += block.nbytes
                    if max_total_bytes is not None and total_bytes > max_total_bytes:
                        msg = (
                            f"Limite de memória excedido ({total_bytes} > {max_total_bytes} bytes)"
                        )
                        raise MemoryError(msg)
                    result[idx_flat] = block
                return result

            # Abordagem via to_delayed
            delayed_flat = delayed_blocks().ravel()
            result = {}
            total_bytes = 0
            for i, delayed_block in enumerate(delayed_flat):
                if max_chunks is not None and len(result) >= max_chunks:
                    break
                block = np.asarray(delayed_block.compute())
                total_bytes += block.nbytes
                if max_total_bytes is not None and total_bytes > max_total_bytes:
                    msg = f"Limite de memória excedido ({total_bytes} > {max_total_bytes} bytes)"
                    raise MemoryError(msg)
                num_chunks = getattr(data, "numchunks", None)
                if num_chunks is None:
                    num_chunks = tuple(len(c) for c in chunks)
                idx = np.unravel_index(i, num_chunks)
                result[idx] = block
            return result

        # Sem chunks (numpy array)
        return {(0, 0, 0): np.asarray(data)}

    # ==========================================================
    # Summary
    # ==========================================================
    def summary(self) -> dict[str, Any]:
        ds = self.dataset
        return {
            "dims": dict(ds.sizes),
            "data_vars": {k: tuple(ds[k].sizes) for k in ds.data_vars},
            "coords": {k: tuple(ds[k].sizes) for k in ds.coords},
            "satellite_names_count": len(self.satellite_names),
            "time_range": self.time_range,
        }
