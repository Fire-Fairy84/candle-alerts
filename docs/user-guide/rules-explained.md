# Conditions y Rules

## Qué es una condition

## Explicación simple

Una `condition` es una comprobación concreta que devuelve solo una de dos respuestas:

- `True`
- `False`

No decide por sí sola una estrategia completa. Solo responde a una pregunta muy específica.

Ejemplos típicos:

- `RSI < 30`
- `close > VWAP`
- `EMA 9 cruza por encima de EMA 21`
- `volumen actual >= 2x volumen medio`

## Qué significa en la práctica

Una condición es la unidad mínima de lógica del bot.

Como usuario, piensa en ella como un interruptor:

- se cumple,
- o no se cumple.

Su utilidad está en que hace el sistema legible. En vez de una "caja negra", puedes entender exactamente qué pregunta hace el bot.

## Ejemplo

`RSI < 30`

Lo que significa realmente es:

"En la vela más reciente, el valor del RSI está por debajo de 30."

No significa:

- que haya giro seguro,
- que el precio esté barato,
- ni que el mercado haya terminado de caer.

Solo significa eso: el RSI actual está en esa zona.

## Errores comunes

- Leer una condición como una promesa.
- Pensar que una condición ya es una estrategia.
- No mirar en qué vela y en qué marco temporal se está evaluando.

---

## Cómo se evalúan las conditions en Candle

## Explicación simple

En Candle, las condiciones se evalúan sobre la vela más reciente de un conjunto de datos ya preparado con indicadores.

Eso quiere decir:

- primero se cargan las velas,
- luego se calculan indicadores,
- y después la condición mira la parte final de ese resultado.

Cada tipo de condición revisa algo distinto:

- `ema_crossover`: compara la vela anterior y la actual
- `rsi_range`: mira si el RSI cae dentro de un rango
- `price_above_vwap`: compara cierre con VWAP
- `volume_spike`: compara el volumen actual con una media de velas anteriores

## Qué significa en la práctica

Tú no necesitas pensar en fórmulas complejas para usarlo.
Lo importante es saber qué pregunta exacta hace cada condición.

Si una alerta parece rara, la mejor pregunta no es "¿por qué el bot falló?" sino:

"¿Qué condición concreta se cumplió para que esta regla saltara?"

## Ejemplo

`volume_spike` con multiplicador `2`

Traducción simple:

"El volumen de la vela actual es al menos el doble del volumen medio de las 20 velas anteriores."

## Errores comunes

- Creer que el volumen se compara contra toda la historia.
- Olvidar que algunas condiciones necesitan suficientes velas para calcularse bien.
- No diferenciar entre la vela actual y las velas anteriores.

---

## Qué es una rule

## Explicación simple

Una `rule` es un conjunto de una o varias condiciones.

En Candle, una regla se cumple solo si todas sus condiciones se cumplen a la vez.

Eso es lógica `AND`.

Dicho fácil:

- una condición sola es una pista,
- una regla es una señal más filtrada.

## Qué significa en la práctica

Las reglas son más útiles que un indicador suelto porque reducen ruido.

Un RSI alto por sí solo puede aparecer muchas veces.
Pero si además exiges otra confirmación, como precio por encima de VWAP o volumen fuera de lo normal, la señal suele quedar más acotada.

Como usuario, debes mirar la regla completa, no solo una condición suelta.

## Ejemplo

Regla simple:

- condición 1: `RSI entre 70 y 100`
- condición 2: `precio > VWAP`

La regla solo salta si ambas son verdaderas en ese momento.

Eso es más informativo que mirar solo una de las dos.

## Errores comunes

- Pensar que una regla es "mejor" solo por tener más condiciones.
- Añadir tantas condiciones que casi nunca salte nada.
- No saber qué parte de la regla aportó valor real.

---

## Por qué las rules son más útiles que un indicador suelto

## Explicación simple

Un indicador aislado te da una sola perspectiva.
Una regla junta varias perspectivas en una misma comprobación.

Eso ayuda a filtrar ruido.

## Qué significa en la práctica

Si recibes una alerta basada en una regla, en general tiene más contexto que una alerta basada en una sola lectura.

Pero cuidado: "más contexto" no significa "certeza". Solo significa que el sistema ha pedido más requisitos antes de avisarte.

## Ejemplo

Comparación rápida:

- Indicador suelto: `RSI = 72`
- Regla: `RSI entre 70 y 100` y `precio > VWAP`

La segunda te cuenta una historia algo más completa que la primera.

## Errores comunes

- Dar valor mágico a una regla compleja.
- Olvidar revisar el gráfico real después de la alerta.
- Pensar que el bot sustituye criterio humano porque combinó dos o tres cosas.

---

## Cómo están definidas las rules en tu proyecto

## Explicación simple

En Candle, las reglas activas se guardan en base de datos y luego se convierten en reglas evaluables por el sistema.

Eso permite que la lógica sea configurable sin meterla toda "a mano" dentro del motor.

## Qué significa en la práctica

Hay tres niveles que conviene distinguir:

- la condición disponible en el código,
- la regla activa guardada en base de datos,
- y la alerta que sale cuando esa regla se cumple.

Ahora mismo, el ejemplo base sembrado en el proyecto es una regla de cruce de `EMA 9/21`.

## Ejemplo

Regla semilla actual:

- nombre: `EMA Crossover 9/21`
- condición: `ema_crossover` con `fast=9` y `slow=21`

## Errores comunes

- Pensar que todas las funciones del proyecto están activas en producción.
- No distinguir entre "regla posible" y "regla realmente encendida".
