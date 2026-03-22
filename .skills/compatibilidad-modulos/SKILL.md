# SKILL: Compatibilidad de Módulos LCD/OLED — EL CELU

## Cuándo usar este skill
Cuando se asigna un código FR (AITECH) a un código Mecánico, o cuando se valida si dos
módulos son intercambiables para reparación. Siempre verificar antes de asumir compatibilidad.

---

## REGLAS GENERALES DE COMPATIBILIDAD

### Regla 1: Marco vs Sin Marco
- **SIN MARCO (S/MARCO)**: solo el vidrio + LCD. Mayor posibilidad de compatibilidad cruzada.
- **CON MARCO (C/MARCO)**: display + frame plástico/metal. Generalmente exclusivo del modelo.
  - Excepción históricamente: algunas líneas Motorola y Samsung A30/A50 admitían C/MARCO cruzado.
  - Hoy (2026): muy rara vez. Tratar C/MARCO como exclusivo salvo evidencia contraria.

### Regla 2: Mismo tamaño ≠ compatible
- 6.4" Moto G8 y 6.4" Moto G8 Power: diferentes conectores internos → NO compatibles.
- Siempre verificar número de modelo XT/SM, no solo tamaño de pantalla.

### Regla 3: Sub-líneas similares
- "Plus", "Power", "Pro", "Max" casi siempre son modelos DISTINTOS con pantallas distintas.
- Excepción confirmada: G7 y G7 Plus SÍ comparten el mismo módulo (ver abajo).

### Regla 4: Tecnología diferente = incompatible
- IPS LCD ≠ OLED/AMOLED (aunque sean mismo tamaño).
- Ejemplo: iPhone XR (LCD) ≠ iPhone X/XS (OLED).

---

## TABLA DE COMPATIBILIDADES VERIFICADAS

### MOTOROLA

| Familia | Compatible entre sí | NO compatible |
|---------|---------------------|---------------|
| G7 + G7 Plus | ✅ SÍ (mismo módulo XT1962/XT1965) | G7 Power (XT1955) ≠; G7 Play (XT1952) ≠; G75 5G (2024) ≠ |
| G7 Play | Solo G7 Play (XT1952) | ≠ G7, G7+, G7 Power |
| G7 Power | Solo G7 Power (XT1955) | ≠ G7, G7+ |
| G8 | Solo G8 (XT2045) | G8 Power (XT2041) ≠; G8 Plus (XT2019) ≠ |
| G8 Power | Solo G8 Power (XT2041) | ≠ G8, G8 Plus |
| G8 Plus | Solo G8 Plus (XT2019) | ≠ G8, G8 Power |
| G10/G20/G30/G10 Power | ✅ SÍ entre sí (cotización 039 confirma) | — |
| G13/G23/G34/G53 | ✅ SÍ entre sí (cotización 039 confirma) | — |
| G24/G24 Power/E14/G04/G04S | ✅ SÍ entre sí (cotización 039 confirma) | — |
| G42 | Solo G42 | — |
| G51 5G/G60/G60S/G40 Fusion | ✅ SÍ entre sí (cotización 039 confirma) | — |
| G9 Plus | Solo G9 Plus — MMOTG9PL (S/MARCO), MMOTG9PLCM (C/MARCO) | G9 Power ≠; G9 Play ≠ |
| G9 Power | Solo G9 Power — MMOTG9PW (S/MARCO), MMOTG9PWCM (C/MARCO) | G9 Plus ≠; G9 Play ≠ |
| G9 Play | G9 Play + E7 Plus — MMOTG9PLAY / MMOTG9PLAYCM ✅ | G9 Plus ≠; G9 Power ≠ |
| G14/G54 5G/G55 | ✅ SÍ entre sí — MMOTG14 dice "MOD MOT G14/G54 5G"; sticker también incluye G55 | — |
| G32/G73 | ✅ SÍ entre sí — sticker Mecánico confirma M G32 + M G73 mismo módulo | — |
| E30/E40 | ✅ SÍ entre sí — sticker Mecánico confirma M E30 + M E40 mismo módulo | — |
| E15/G05/G15/G15 Power | ✅ SÍ entre sí — MMOTE15 = "MOD MOT E15/G05"; sticker confirma G15 Power también | — |

### SAMSUNG

| Familia | Compatible entre sí | NO compatible |
|---------|---------------------|---------------|
| A10 | Solo A10 (SM-A105) — AMOLED | A10S (SM-A107) ≠ (A10S es IPS LCD) |
| A10S | A10S + A107 | ≠ A10 (diferente tecnología) |
| A11 | A11 + M11 (S/MARCO) | — |
| A12 UNI | A12/A125F/A127/A02/A32 5G | Gran familia — verificar variantes |
| A12 C/MARCO | A12/A125F/A127 | Versión más restringida |
| A13 4G | A13 4G/A135/A137 | — |
| A13 4G MULTI | A13 4G + A23 4G/5G + M23/M33/M336B | Amplio — cotización 039 lo confirma |
| A22 4G | Solo A22 4G | A22 5G ≠ (diferente tecnología) |
| A22 5G | Solo A22 5G | A22 4G ≠ |
| A24 | Solo A24 4G | — |
| A30/A50/A50S | ✅ Sí entre sí (C/MARCO) | — |
| A30S | Solo A30S | — |
| A31 | Solo A31 | — |
| A02S/A03/A03S/A04E | ✅ SÍ entre sí (módulo UNIVERSAL) | — |

### APPLE (iPhone)

| Familia | Compatible entre sí | NO compatible |
|---------|---------------------|---------------|
| iPhone X | X + XS ✅ (mismo panel OLED 5.8") | XR ≠ (LCD 6.1"); XS Max ≠ (6.5") |
| iPhone XR | Solo XR (LCD 6.1") | ≠ X, XS, XS Max |
| iPhone XS Max | Solo XS Max (OLED 6.5") | ≠ X, XS |
| iPhone 11 | Solo 11 (LCD 6.1") | 11 Pro ≠; 11 Pro Max ≠ |
| iPhone 11 Pro | Solo 11 Pro (OLED 5.8") | 11 ≠; 11 Pro Max ≠ (6.5") |
| iPhone 11 Pro Max | Solo 11 Pro Max (OLED 6.5") | ≠ 11 Pro |
| iPhone 13 | Solo 13 (OLED 6.1") | 13 Pro ≠ (ProMotion 120Hz diferente); 13 Pro Max ≠ (6.7") |
| iPhone 13 Pro | Solo 13 Pro | ≠ 13, ≠ 13 Pro Max |
| iPhone 13 Pro Max | Solo 13 Pro Max | ≠ 13 Pro |

---

## ERRORES HISTÓRICOS DETECTADOS (para no repetir)

| Error | Corrección | Impacto |
|-------|------------|---------|
| MMOTG75 asignado a G7/G7+ | MMOTG75 = G75 5G (2024), completamente diferente | Demanda inflada de 4.57 → 1.87 u/día |
| MMOTG7PW asignado a G7/G7+ | G7 Power ≠ G7/G7+ | Demanda sobreestimada |
| MMOTG8PW + MMOTG8PLU asignados a G8 | G8/G8P/G8+ son todos incompatibles entre sí | Demanda inflada |
| MIPHXR + MIPHXSMAX asignados a IPH X | XR=LCD diferente; XS Max=6.5" diferente | Demanda inflada de 4.57 → 0.93 u/día. El XR (446 uds) era el mayor volumen |
| MIPH13PRHOLD + MIPH13PRMHOLD asignados a IPH 13 | 13 Pro tiene ProMotion; 13 Pro Max es 6.7" | Demanda inflada de 1.62 → 0.71 u/día |
| MIPH11PRMAX asignado a IPH 11 Pro | 11 Pro Max es 6.5" vs 5.8" | Mínimo impacto |
| MSAMA10SCM + MSAMA10S + MSAMA10SCR asignados a SAM A10 | A10=AMOLED; A10S=IPS LCD — incompatibles | Demanda inflada de 22.19 → 0.76 u/día. El A10S (1059 uds) era el mayor volumen |
| G9 Power sin FR codes en análisis | MMOTG9PW (117u SJ) + MMOTG9PWCM (1u) = 118u fr_activo → 27 días → CANCELAR | Hubiera ordenado 48u × U$S 6.52 = U$S 313 innecesarios |
| E7 Plus sin FR codes en análisis | MMOTG9PLAY (903u SJ) cubre G9 Play Y E7 Plus → 295 días → CANCELAR | Hubiera ordenado 94u × U$S 5.94 = U$S 558 innecesarios |
| MSAMA30SOLD mal interpretado | MSAMA30SOLD = "MOD SAM A30S OLED" (no es "A30 OLD") — asignación a A30S MEC es CORRECTA | Sin impacto, solo aclaración |

---

## FUENTES RECOMENDADAS PARA VERIFICAR COMPATIBILIDAD

1. **Cotización Mecánico** — columna "MODELO STICKER" lista todos los modelos compatibles
2. **all-spares.com** — base de datos de repuestos, lista 5-8 modelos compatibles por módulo
3. **mobilesentrix.com** — proveedor mayorista, organizado por familia de modelos (bueno para Motorola)
4. **MercadoLibre Argentina** — publicaciones de vendedores que listan compatibilidad explícita
5. **AliExpress** — listings de proveedores chinos con códigos XT/SM compatibles

---

## PROTOCOLO PARA CRUZAR FR ↔ MEC

1. Comparar nombre completo del artículo (no solo modelo base)
2. Verificar si incluye "C/MARCO" o "S/MARCO" — C/MARCO es más restrictivo
3. Si el nombre tiene sub-variante (Power, Plus, Pro, Max, Play) → buscar explícitamente
4. Buscar en cotización Mecánico columna MODELO STICKER para ver compatibilidad oficial
5. Si hay dudas → buscar en MercadoLibre AR o all-spares.com antes de asumir
6. Tecnología diferente (LCD vs OLED vs AMM) → incompatible aunque sea mismo tamaño

---

## CÓDIGOS FR DECODIFICADOS (prefijos)

| Prefijo | Marca |
|---------|-------|
| MSAM | Samsung |
| MMOT | Motorola |
| MIPH | iPhone |
| MXI / MRED | Xiaomi / Redmi |
| MALC | Alcatel |
| MTCL | TCL |
| MLG | LG |
| MZTE | ZTE |

Sufijos comunes:
- `CM` = C/MARCO (with frame)
- `CR` = Crown (variante)
- `SM` = Sin Marco (without frame) o variante estándar
- `PW` = Power
- `PLU` = Plus
- `TO` / `T2O` = Tipo 2 Oscuro (variante de calidad)
- `OLD` = modelo viejo / primera generación
