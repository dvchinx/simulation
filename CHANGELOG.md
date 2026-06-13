# Changelog

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
