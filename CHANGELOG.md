# Changelog

## v3.0.0 — 2026-06-16

- **Terreno variable:** el grid se genera con ruido aleatorio suavizado (25 iteraciones de promedio de vecinos) que produce zonas orgánicas de agua (azul), roca (gris) y pantano (verde oscuro). La roca es infranqueable para cualquier especie; agua y pantano elevan el costo metabólico de moverse (×1.6 y ×1.3 respectivamente). Las crías no pueden nacer en roca. El pasto no regenera en roca.

- **Biomas:** capa separada sobre el terreno con 4 biomas generados a escala mayor (40 iteraciones): templado, ártico, desierto y tropical. Cada bioma aplica offsets de temperatura (`±0.5`) y multiplicadores de regeneración de pasto (`×0.3` a `×1.8`), creando nichos ecológicos visibles: las poblaciones prosperan en zonas tropicales y colapsan en el ártico o desierto sin adaptación genómica.

- **Ciclos de estaciones / temperatura:** temperatura global = `sin(2π·tick / 400) × 0.85`, con offset adicional por bioma. Efectos: (1) velocidad de movimiento reducida hasta 80% en extremos (`TEMP_SPEED_FACTOR = 0.4`); (2) umbral de reproducción aumentado hasta +25 energía en invierno ártico; (3) tasa de regeneración de pasto cae hasta 5% del valor base. El sidebar muestra estación actual (Primavera/Verano/Otoño/Invierno) y valor numérico de temperatura.

- **Difusión de nutrientes:** grilla `nutrient[y,x] = float32` que se actualiza cada tick con la ecuación de difusión estable (`D=0.05`, decaimiento `0.92`). El pasto deposita nutriente en su celda; éste se difunde hacia las adyacentes creando gradientes suaves. Los herbívoros lo usan como señal de quimiotaxis de largo alcance (`weight=0.12`), lo que produce flujos organizados hacia zonas ricas antes de tener línea de visión directa. El nutriente también potencia levemente la regeneración del pasto en áreas ricas.

- **Perturbaciones periódicas:** fuego cada 500 ticks (círculo de radio 12, limpia organismos + pasto + marca naranja que decae) e inundación cada 750 ticks (franja horizontal de 20 celdas, marca azul). Ambas dejan rastro visual decayente en canvas; la comunidad recoloniza desde los bordes de la zona afectada, visible como sucesión ecológica.

- **Renderizado de Fase 5:** orden de prioridad (menor a mayor): terreno → territorio → feromona → pasto → organismos → inundación → fuego. La roca siempre muestra su color (los organismos nunca la ocupan). Las perturbaciones activas tienen máxima prioridad visual en celdas vacías.

- **Estructura de datos nueva:** `terrain[y,x]`, `biome[y,x]`, `nutrient[y,x]`, `fire[y,x]`, `flood[y,x]` (todas float32/uint8 paralelas). `tick_count` movido al estado de simulación; `global_temperature` y `local_temperature[y,x]` calculados cada tick por `rules/temperature.py`.


## v2.0.0 — 2026-06-14

- **Feromonas y quimiotaxis:** cada organismo deposita una traza química en la celda que ocupa. Las feromonas se difunden a las celdas vecinas mediante un stencil de 5 puntos y decaen exponencialmente (~15% por tick). Los herbívoros siguen el rastro propio de su especie (`PHEROMONE_HERB_ATTRACTION = 0.5`), lo que genera autopistas emergentes y migración en grupo. Los depredadores rastrean la feromona combinada de ambas especies presa (`PHEROMONE_PRED_ATTRACTION = 0.7`), permitiendo caza en zonas recientemente visitadas aunque no haya presa en línea de visión. Implementación: grilla `pheromone[y, x, 3] = float32` con capa por especie.

- **Cardumen / Bandada (Flocking):** los herbívoros aplican reglas de cardumen con dos fuerzas opuestas — cohesión (atracción hacia el centro de masa de congéneres en radio 6, ponderada por distancia) y separación (repulsión de congéneres a radio 2). El resultado es movimiento en grupo con espaciado natural: organismos forman bandadas que se desplazan juntas sin control central. Herbívoro A y B forman cardúmenes independientes. Implementación: `rules/flocking.py` precomputa campos vectoriales `(H, W, 4)` de puntuación direccional cada tick.

- **Comportamiento territorial:** cada organismo "marca" la celda que ocupa con una señal territorial de decaimiento muy lento (~0.5% por tick → persiste ~200 ticks). Los herbívoros se sienten atraídos hacia su propio territorio (`TERRITORY_ATTRACTION = 0.15`) y huyen del territorio del depredador (`TERRITORY_FEAR_WEIGHT = 0.30`), creando zonas de seguridad y zonas de peligro visibles. Implementación: grilla `territory[y, x, 3] = float32`.

- **Visualización de capas:** el canvas muestra rastros de feromona en tonos tenues sobre celdas vacías (verde para herb_a, rojo para predadores, azul para herb_b), y marcas territoriales en tonos aún más apagados debajo. Prioridad de renderizado: organismos > infectados > pasto > feromona > territorio. Sidebar añade contador de celdas territoriales por especie en tiempo real.

- **Integración de señales en el movimiento:** los herbívoros combinan en un solo vector de puntuación por dirección: comida visible (score dominante, 0–1.0), feromona propia (hasta 0.5), cohesión/separación de cardumen, y atracción/miedo territorial. El argmax del vector combinado determina el movimiento. Sin ninguna señal, el movimiento sigue siendo aleatorio.



## v1.1.0 — 2026-06-12

- **Genoma heredable:** cada organismo lleva un mini-genoma de 5 genes (`float32[5]`): velocidad, umbral de reproducción, eficiencia alimentaria, rango de visión y tasa de mutación. Grilla paralela `genome[y, x, 5]`.
- **Visión inteligente en herbívoros:** los herbívoros escanean en 4 direcciones hasta su rango de visión genómico y sesgan el movimiento hacia la comida más cercana. Sin comida visible, caminan aleatoriamente.
- **Visión variable en depredadores:** el rango de visión del depredador es ahora individual por genoma (antes fijo en 4). Depredadores con mayor visión cazan más eficientemente.
- **Selección natural emergente:** la velocidad, la eficiencia y el umbral de reproducción crean presión selectiva real. Organismos con genes favorables sobreviven más y se reproducen antes.
- **Velocidad como trade-off:** organismos más rápidos se mueven con mayor probabilidad por tick pero pagan más coste metabólico. El óptimo evolutivo depende de la densidad de pasto.
- **Eficiencia alimentaria:** herbívoros ganan `FOOD_ENERGY_GAIN × eficiencia` por comer pasto; depredadores ganan `PREDATOR_ENERGY_FROM_PREY × eficiencia` por cada presa. Ambos genes evolucionan hacia arriba.
- **Tasa de mutación como gen:** la mutación en cada cría se escala por el gen de tasa de mutación del padre. Alta mutación → evolución rápida pero inestable; baja → estabilidad.
- **Panel de evolución:** sidebar muestra los 5 genes medios por especie en tiempo real, permitiendo observar la evolución generación a generación.

## v1.0.0 — 2026-06-11

- **Caza dirigida:** los depredadores escanean 8 celdas en cada una de las 4 direcciones cardinales y se mueven hacia la presa más cercana (puntuación 1/distancia). Empates se rompen aleatoriamente. Si no detectan presa en ningún rango, siguen movimiento aleatorio. Algoritmo completamente vectorizado con NumPy — sin loops Python por celda.

## v0.3.0 — 2026-06-11

- **Depredador-Presa:** especie roja (depredador) caza herbívoros adyacentes, gana 60 de energía al comer y muere de vejez a los 80 ticks. Genera ciclos de Lotka-Volterra visibles.
- **Herbívoro B:** segunda especie herbívora (azul) que compite con el herbívoro A por el mismo pasto. Exclusión competitiva y oleadas de color emergentes.
- **Infección:** los herbívoros pueden contagiarse por proximidad (15% por tick). Los infectados aparecen en amarillo/naranja y pierden 5 de energía por tick. Recuperación espontánea al 2%. Los depredadores son inmunes. La infección se transmite a las crías.
- **Sidebar actualizado:** 5 barras en tiempo real — Herbív. A, Depredadores, Herbív. B, Infectados, Pasto.
- **Responsive y zoom:** layout adaptado para móvil (scroll wheel, pinch, drag). Doble clic/tap para resetear zoom.

## v0.2.0 — 2026-06-10

- **Sistema de energía:** cada célula tiene energía (0-255). Costo metabólico de 2 por tick. Muere si llega a 0.
- **Pasto:** capa de alimento en el grid. Las células ganan 20 de energía al pisar pasto. El pasto se regenera aleatoriamente en celdas vacías.
- **Reproducción:** al acumular 100 de energía, la célula genera una cría en una celda adyacente vacía y resetea su energía.
- **Envejecimiento:** cada célula muere tras 150 ticks de vida.
- **Medidor de población:** sidebar muestra Tick, Vivos, Pasto y Vacías con barras en tiempo real.

## v0.1.0 — 2026-06-10

- Simulación inicial con 1 especie (verde) que se mueve aleatoriamente
- Grid de 200×200 celdas, ~100 células iniciales
- Transmisión en tiempo real vía WebSocket a 1 FPS
- Vista pixeleada escalada a 600×600 en el navegador
