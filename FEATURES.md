# Features — Life Simulation 2D

Ideas organizadas por complejidad y valor visual. Las más impactantes para un observador primero.

---

## Fase 1 — Ciclos de vida (base de todo lo demás)

### Sistema de energía
Cada célula tiene energía. Moverse cuesta energía. Si llega a 0, muere.  
**Desbloquea:** muerte por inanición, ciclos de población, presión de selección natural.  
**Implementación:** grilla paralela `energy[y, x] = uint8`.

### Reproducción
Cuando una célula alcanza energía máxima, genera una cría en una celda adyacente vacía.  
**Desbloquea:** crecimiento de población, colapsos por sobrepoblación, boom/bust cíclicos.

### Envejecimiento
Cada célula tiene un contador de edad. Muere tras N ticks (senescer).  
**Desbloquea:** rotación generacional, ondas demográficas visibles.  
**Complejidad:** baja — grilla paralela `age[y, x] = uint8`.

### Capa de alimento / pasto
Celdas con alimento que se regeneran con el tiempo. Las células herbívoras ganan energía al pisar pasto.  
**Desbloquea:** forrajeo heterogéneo, manadas migrando a zonas ricas, hambrunas locales.  
**Implementación:** grilla paralela `food[y, x] = uint8`. Se incrementa cada tick, herbívoros la decrementan.

---

## Fase 2 — Múltiples especies e interacciones

### Depredador-Presa (2 especies)
Especie A (presa) come pasto. Especie B (depredador) come a la especie A y gana su energía.  
**Desbloquea:** ciclos de Lotka-Volterra — el fenómeno más bello de ver en pantalla.  
**Visual:** oleadas de depredadores, extinción local, recuperación, rebote.

### Competencia entre herbívoros
2+ especies que no se comen entre sí pero compiten por el mismo pasto.  
**Desbloquea:** exclusión competitiva, oleadas de color reemplazando a otra especie.  
**Complejidad:** baja — solo agregar especie con los mismos parámetros.

### Parasitismo / Infección
Un parásito reduce la energía del huésped sin matar directamente. Se contagia por proximidad.  
**Desbloquea:** olas de enfermedad, colapsos de población, inmunidad por supervivencia.  
**Visual:** overlay de "infectados"; la enfermedad se propaga como incendio.

---

## Fase 3 — Evolución

### Rasgos heredables y genoma
Cada célula lleva un mini-genoma (`float32[4-8]`): velocidad, umbral de reproducción, eficiencia energética, rango de visión.  
Al reproducirse, los genes se copian con mutación (ruido gaussiano pequeño).  
**Desbloquea:** evolución observable, deriva genética, carreras armamentistas entre especies.

### Visión y movimiento inteligente
Si el genoma incluye un gen de "rango de visión", la célula detecta comida o depredadores y sesga su movimiento.  
**Desbloquea:** forrajeo realista, presas que huyen, cazadores que persiguen.  
**Visual:** en vez de ruido, flujos organizados hacia recursos.

### Selección natural
Solo las células con mayor fitness (energía + edad) pueden reproducirse. Las demás mueren con mayor probabilidad.  
**Desbloquea:** evolución dirigida observable; la presión de selección moldea rasgos en tiempo real.

### Tasa de mutación como gen
Uno de los genes codifica la tasa de mutación. Alta mutación = evolución rápida pero inestable. Baja = estabilidad.  
**Desbloquea:** estrategias evolutivas meta-nivel; poblaciones estables vs. caóticas coexistiendo.

---

## Fase 4 — Comportamientos físicos y colectivos

### Feromonas
Las células dejan un rastro químico que se difunde y decae. Sus congéneres se atraen hacia él.  
**Desbloquea:** comportamiento de hormiga, autopistas emergentes, migración en grupo.  
**Visual:** rastros que brillan y se desvanecen; flujos organizados a partir de cero.  
**Implementación:** grilla `pheromone[y, x] = float32`. Se incrementa al pasar, convolución de difusión + decaimiento cada tick.

### Gradientes y quimiotaxis
Las células calculan el gradiente local de comida/peligro y sesgan movimiento hacia la dirección favorable.  
**Desbloquea:** forrajeo tipo río, convergencia de swarms en recursos.  
**Visual:** las células "fluyen" hacia zonas ricas como agua cuesta abajo.

### Comportamiento de cardumen / bandada
Las células consideran la velocidad y dirección de sus vecinas cercanas (reglas de flocking: separación, alineación, cohesión).  
**Desbloquea:** murmuros de estorninos, movimiento sincronizado emergente sin control global.  
**Visual:** hipnótico. Uno de los mejores efectos visuales posibles.

### Comportamiento territorial
Las células marcan territorio y "defienden" celdas cercanas contra otras especies.  
**Desbloquea:** fronteras visibles, frentes de guerra, jerarquías espaciales emergentes.  
**Visual:** zonas de color con bordes que se mueven lentamente.

---

## Fase 5 — Ambiente dinámico

### Ciclos de temperatura / estaciones
Temperatura global varía con un seno cíclico. Afecta velocidad de movimiento y reproducción.  
**Desbloquea:** migración estacional, sincronización de población, especialización noche/día.  
**Implementación:** `temperature = sin(tick / period) * amplitude`. Bajo costo.

### Terreno variable
Celdas con tipos de terreno: libre, agua (lento), roca (infranqueable), pantano (caro en energía).  
**Desbloquea:** cuellos de botella migratorios, islas, corredores naturales.

### Difusión de recursos
Los nutrientes se difunden hacia celdas adyacentes cada tick (como calor). Crea gradientes suaves.  
**Desbloquea:** quimiotaxis, organización espacial emergente, patrones tipo Turing.  
**Implementación:** convolución de la grilla de comida con kernel de difusión.

### Biomas
El grid se divide en zonas con distintas tasas de regeneración de comida, temperatura y velocidad base.  
**Desbloquea:** especialización por nicho, rutas migratorias emergentes.

### Perturbaciones (fuego, inundación, extinción local)
Eventos periódicos o manuales que borran una región. La comunidad recoloniza.  
**Desbloquea:** prueba de resiliencia, sucesión ecológica visible.

---

## Visualización (alto impacto, bajo costo)

### Gráfico de población en tiempo real
Líneas de tiempo por especie actualizadas cada tick en el sidebar.  
**Desbloquea:** ver ciclos de Lotka-Volterra cuantitativamente, detectar colapsos.  
**Implementación:** servidor lleva historial de 1000 ticks; envía como JSON junto al frame.

### Heatmaps intercambiables
Toggle para ver: densidad de población, energía promedio, temperatura, feromonas, comida.  
**Implementación:** grilla de uint8 adicional por overlay. Bajo costo, alto valor interpretativo.

### Trails / estelas de movimiento
Las celdas recuerdan cuándo fue la última visita. Se renderizan con alpha decayendo.  
**Visual:** ver patrones de movimiento de un vistazo; identificar rutas habituales.

### Colorear por rasgo
Si hay genoma: colorear cada célula por el valor de un gen dominante (ej. rojo=rápido, azul=lento).  
**Visual:** ver evolución suceder en pantalla; oleadas de color reemplazando a otras.

---

## Control de simulación

| Feature | Complejidad | Descripción |
|---|---|---|
| Pause / Resume / Step | Baja | El cliente envía un comando; el servidor pausa el loop |
| Multiplicador de velocidad | Baja | Ajustar `interval = 1.0 / (FPS * multiplier)` |
| Reset / Reseed | Baja | `state["grid"] = create_grid()` |
| Spawner por especie | Baja | Sembrar N células de una especie en posición aleatoria |
| Snapshot a disco | Media | Guardar estado como `.npy` o pickle; restaurar desde checkpoint |
| API de parámetros | Media | Endpoint HTTP para cambiar config.py en caliente |

---

## Fenómenos emergentes esperados

| Combinación de features | Qué se ve |
|---|---|
| Energía + Reproducción | Ciclos boom/bust de una sola especie |
| + Depredador | Ciclos de Lotka-Volterra oscilando |
| + Velocidad heredable | Presas evolucionan más rápido; depredadores las alcanzan |
| + Feromonas | Caza organizada en manada; colonias hormiga |
| + Biomas | Presas se refugian en terreno hostil para depredadores |
| + Visión + Gradientes | Flujos organizados; forrajeo inteligente emergente |
| + Flocking | Murmuros sincronizados sin control central |
| Difusión + Gradientes | Patrones tipo Turing: rayas, manchas, laberintos |
| Tasa de mutación como gen | Poblaciones estables vs. caóticas coexistiendo |
| Perturbaciones + Sucesión | Frontera de colonización avanzando sobre zona destruida |

---

## Estructura de datos — evolución sugerida

**Ahora (v0.1):**
```python
grid[y, x] = uint8  # 0=vacío, 1=especie
```

**Fase 1–2:**
```python
species[y, x] = uint8
energy[y, x]  = uint8
age[y, x]     = uint8
food[y, x]    = uint8
```

**Fase 3+:**
```python
species[y, x]    = uint8
energy[y, x]     = uint8
age[y, x]        = uint8
genome[y, x]     = float32[8]
pheromone[y, x]  = float32   # por especie
terrain[y, x]    = uint8
food[y, x]       = uint8
temperature[y, x]= float32
```

Grillas paralelas (arrays separados) son más rápidas en numpy que `structured_array`.
