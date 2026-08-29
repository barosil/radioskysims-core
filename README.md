# radioskysims-core

Kernel compartilhado do ecossistema **RadioSkySim** — camada base sem
dependência de pacotes de domínio pesados (`beam`, `skymap`, `sources`,
`simulation`).

## Conteúdo

- `config` — `ConfigPort` (ABC) + `TomlConfigAdapter` + API legada `config_loader`
- `db` — `Database`/`AsyncDatabase` + registro de modelos SQLModel plugável
- `logging_config` — logging estruturado em JSON
- `paths` — `PathManager` / resolução da raiz do projeto
- `monitor` — `SystemMonitor` (CPU/memória/disco)
- `progress` — indicador de progresso uniforme
- `domain.common` — `Observer`, `TimeRange`, `FrequencyRange`, exceções, `ScienceValidator`
- `domain.geometry` — `SkyfieldGeometryProvider`, `compute_pointing_track`
- `domain.tracks` — `TrackFactory`
- `application.ports.geometry` — contrato `GeometryProviderPort`
- `skyfield_loader` — loader/cache de efemérides Skyfield

## Dependências

Mínimas: `numpy`, `astropy`, `xarray`, `dask`, `skyfield`, `pydantic`,
`sqlmodel`, `psutil`, `python-dotenv`. **Sem** `panel`, `healpy`, `pyccl`,
`camb`, `astroquery`, `georinex`.

## Testes

```bash
uv run --package radioskysims-core pytest
```
