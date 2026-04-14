# Errores comunes al usar Candle

## Error 1: pensar que una alerta es una orden

## Explicación simple

Una alerta no es una instrucción.
Es un aviso de que una regla se ha cumplido.

## Qué significa en la práctica

Tu trabajo empieza cuando llega la alerta, no termina ahí.

Debes revisar:

- contexto,
- marco temporal,
- claridad de la señal,
- y si esa alerta encaja con lo que tú querías vigilar.

## Ejemplo

Una alerta por `RSI Oversold` solo te dice que el RSI está en una zona baja según la regla. No te dice cómo evolucionará el precio después.

## Errores comunes

- Obedecer la alerta.
- Darle valor automático.

---

## Error 2: quedarse con el nombre sin entender la regla

## Explicación simple

Nombres como `EMA Crossover 9/21` o `Price Above VWAP` suenan claros, pero si no sabes qué preguntan exactamente, te puedes confundir.

## Qué significa en la práctica

Cada vez que veas una alerta, tradúcela a lenguaje normal.

Ejemplo de traducción útil:

- `EMA Crossover 9/21` = la media rápida acaba de ponerse por encima de la lenta
- `Price Above VWAP` = el cierre actual está por encima del precio medio ponderado por volumen

## Ejemplo

Si no haces esa traducción, puedes pensar que el bot detectó algo más complejo de lo que realmente detectó.

## Errores comunes

- Asumir demasiado a partir del nombre.
- No comprobar qué condición hay detrás.

---

## Error 3: ignorar el marco temporal

## Explicación simple

Una señal en `4h` y una señal en `1d` pueden parecer iguales por nombre, pero no tienen el mismo peso ni la misma velocidad.

## Qué significa en la práctica

Antes de valorar una alerta, mira siempre el `timeframe`.

Eso cambia:

- la velocidad del movimiento,
- la cantidad de ruido,
- y la paciencia que requiere interpretar la señal.

## Ejemplo

Un cruce en `4h` puede aparecer y desaparecer con más frecuencia que una estructura en `1d`.

## Errores comunes

- Juntar todas las alertas como si fueran equivalentes.
- No ajustar tu lectura al timeframe.

---

## Error 4: confiar en indicadores aislados

## Explicación simple

Un indicador por sí solo enseña solo una parte de la película.

## Qué significa en la práctica

Cuando una alerta nace de una sola lectura, conviene revisar si el precio y el contexto acompañan.

Por eso las reglas con varias condiciones pueden ser más útiles: no porque sean mágicas, sino porque piden más de una confirmación.

## Ejemplo

`RSI > 70` puede aparecer muchas veces durante una fase fuerte.
Eso no convierte cada aparición en una señal especialmente útil.

## Errores comunes

- Sacar conclusiones grandes a partir de una sola métrica.
- No mirar el gráfico real.

---

## Error 5: pensar que más alertas es mejor

## Explicación simple

Muchas alertas pueden significar más ruido, no más calidad.

## Qué significa en la práctica

Un buen sistema de alertas no es el que más mensajes manda, sino el que te ayuda a centrarte.

Si el flujo de alertas te satura, probablemente necesitas revisar cómo las interpretas o qué reglas estás vigilando.

## Ejemplo

Si un mercado está lateral, los cruces y pequeñas variaciones pueden generar varios avisos con poca utilidad práctica.

## Errores comunes

- Medir la utilidad del bot por cantidad de mensajes.
- Entrar en modo reacción continua.

---

## Error 6: no aceptar que algunas alertas se descartan

## Explicación simple

Parte del buen uso del bot es aceptar que muchas alertas solo sirven para mirar y descartar.

## Qué significa en la práctica

Eso no significa que el bot falle.
Significa que una alerta cumple su función: señalar algo para revisar.

Tu criterio consiste también en decir "esto no me interesa ahora".

## Ejemplo

Una alerta técnicamente correcta puede llegar en una zona del gráfico demasiado confusa como para ser útil.

## Errores comunes

- Esperar que cada alerta sea especial.
- Frustrarte cuando una señal no parece valiosa al revisarla.
