# Indicadores explicados

## RSI

## Explicación simple

El `RSI` mide la fuerza del movimiento reciente del precio en una escala de `0` a `100`.

No te dice si algo "va a pasar". Te dice si el movimiento reciente ha sido relativamente fuerte hacia arriba o hacia abajo.

Una forma simple de leerlo:

- RSI bajo: el precio viene de debilidad reciente.
- RSI alto: el precio viene de fuerza reciente.

En muchos usos básicos:

- por debajo de `30` suele interpretarse como zona de debilidad fuerte,
- por encima de `70` suele interpretarse como zona de fuerza alta.

## Qué significa en la práctica

Como usuario, debes mirar el RSI como una pista, no como una sentencia.

En Candle aparece dentro de reglas como:

- `RSI Oversold`
- `RSI Overbought`
- o rangos tipo `RSI < 30` / `RSI entre 70 y 100`

Lo importante es preguntarte:

- ¿el RSI está extremo de verdad o solo un poco alto/bajo?
- ¿esa lectura coincide con lo que ves en el precio?
- ¿el mercado está lateral o con tendencia clara?

## Ejemplo

`RSI < 30`

Eso no significa "ahora toca subir".
Significa algo más simple:

"En las últimas velas, el precio ha mostrado una debilidad fuerte comparada con su comportamiento reciente."

Si Candle dispara una alerta por eso, lo que tú deberías mirar es:

- si el precio sigue cayendo con fuerza,
- si esa lectura aparece en una zona relevante del gráfico,
- y si la señal está sola o acompañada por otras confirmaciones.

## Errores comunes

- Pensar que `RSI < 30` garantiza rebote.
- Pensar que `RSI > 70` siempre implica giro inmediato.
- Usar RSI aislado sin mirar precio, contexto y marco temporal.

---

## VWAP

## Explicación simple

El `VWAP` es una media del precio ponderada por volumen.

Dicho fácil: no trata igual todas las velas; da más peso a los movimientos donde hubo más actividad.

Sirve para comparar el precio actual con un precio medio "importante" por volumen.

## Qué significa en la práctica

En este bot aparece la condición `price_above_vwap`, que pregunta:

"¿El cierre actual está por encima del VWAP?"

Si la respuesta es sí, Candle lo interpreta como un sesgo de fuerza relativa en ese momento.

Como usuario, debes mirar:

- si el precio está ligeramente por encima o claramente por encima,
- si acaba de cruzarlo o lleva tiempo separado,
- y si ese movimiento va acompañado por volumen o por inercia débil.

## Ejemplo

`close > vwap`

Significa:

"El cierre actual está por encima del precio medio ponderado por volumen calculado en la serie que está usando el bot."

Eso puede sugerir fortaleza relativa, pero no significa que el movimiento vaya a continuar.

## Errores comunes

- Tratar `precio > VWAP` como una señal suficiente por sí sola.
- Ignorar que el VWAP depende de la serie de datos usada.
- Pensar que estar encima del VWAP siempre es "bueno". Depende del contexto.

---

## EMA

## Explicación simple

La `EMA` es una media móvil que da más peso a los datos recientes.

En Candle se calculan:

- `EMA 9`
- `EMA 21`
- `EMA 50`
- `EMA 200`

Cuanto más corta es la EMA, más rápido reacciona.
Cuanto más larga es, más lenta pero más estable.

## Qué significa en la práctica

Las EMAs sirven para ver dirección y cambios de ritmo.

En tu bot, la más importante para alertas actuales es el cruce entre:

- `EMA 9` (rápida)
- `EMA 21` (más lenta)

Si la EMA rápida pasa de debajo a encima de la lenta, Candle lo interpreta como cambio de impulso.

Como usuario, debes mirar:

- si el cruce acaba de ocurrir o llegó tarde,
- si el precio acompaña el cruce,
- y si el mercado está ordenado o con mucho ruido.

## Ejemplo

Cruce `EMA 9` sobre `EMA 21`:

- vela anterior: `EMA 9 < EMA 21`
- vela actual: `EMA 9 >= EMA 21`

Eso es exactamente lo que Candle comprueba para esa condición.

## Errores comunes

- Pensar que cualquier cruce es útil.
- Olvidar que en mercados laterales puede haber muchos cruces falsos.
- Quedarte con el nombre del cruce sin mirar el gráfico.

---

## Indicadores que existen en el proyecto pero no son el centro actual

## Explicación simple

En el código también aparecen otros indicadores, como:

- `SMA`
- `MACD`
- `Stochastic`
- `OBV`
- `CVD`

Pero según la parte principal del sistema, los que se usan de forma estándar para el screener actual son sobre todo:

- `EMA`
- `RSI`
- `VWAP`
- y el volumen para detectar picos

## Qué significa en la práctica

Si ves esos otros nombres en el proyecto, no significa que el bot los esté usando ahora mismo para todas las alertas. Conviene distinguir entre:

- indicadores disponibles en el código,
- indicadores realmente calculados en el flujo estándar,
- e indicadores usados por reglas activas.

## Ejemplo

Que exista una función `macd()` no significa automáticamente que haya una regla activa basada en MACD.

## Errores comunes

- Confundir "está implementado" con "está activo".
- Pensar que cuantos más indicadores haya en el proyecto, mejor decide el sistema.
