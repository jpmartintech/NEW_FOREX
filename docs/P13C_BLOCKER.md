# P13C — Bloqueo de ejecución

El protocolo y el orquestador están congelados y validados, pero la ejecución completa no se ha cerrado.

- Protocolo: `f070e6c6`; SHA256 `216ba43c800e68b6d53aa6eb32193ba82388130d59456828e421fe41c442d7c2`.
- Implementación: `5c999462`, con correcciones de particiones y rendimiento en `e536df3b`, `8d14df91` y `17c78262`, `3313f5ac`.
- G001–G003 completadas y conservadas en `reports/p13c_artifacts/`; checkpoint reproducible.
- G004 fue iniciada y no se considera completada.
- No se abrió el holdout y no se generaron operaciones reales.

El tiempo observado para una generación completa, incluyendo ledgers de las composiciones seleccionadas y ambos controles, es aproximadamente 5–6 minutos. La proyección para 54 generaciones excede varias horas y requiere varios GB adicionales de artefactos Parquet. La ejecución se detuvo por este límite externo de cómputo/almacenamiento interactivo, no por resultados financieros ni por una relajación metodológica.

No existe un informe P13C de resultados ni un tag de fase. Los artefactos parciales no deben interpretarse como una evaluación de 54 meses.
