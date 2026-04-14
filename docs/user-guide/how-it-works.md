# Candle: cómo funciona

## Explicación simple

Candle es un sistema de alertas, no un sistema que actúe por ti.

Su trabajo real es este:

1. Recoge velas de mercado (`OHLCV`).
2. Calcula indicadores sobre esas velas.
3. Comprueba si se cumplen ciertas condiciones.
4. Agrupa esas condiciones dentro de reglas.
5. Si una regla se cumple, genera una alerta.

La idea importante es separar bien cada capa:

- Los datos dicen qué ha pasado en el mercado.
- Los indicadores resumen esos datos.
- Las condiciones hacen preguntas simples sobre esos indicadores.
- Las reglas juntan varias preguntas para decidir si hay una señal.
- La alerta solo te avisa de que esa señal ocurrió.

## Qué significa en la práctica

Si quieres entender tu bot sin liarte, piensa en él como una cadena de filtros:

- Primero entra información bruta del mercado.
- Luego el sistema la traduce a números más fáciles de leer.
- Después revisa si algunos de esos números encajan con una idea concreta.
- Si encajan, te manda un aviso.

Lo importante para ti como usuario es no saltarte pasos. Una alerta no nace "de la nada": nace porque antes hubo datos, cálculo y evaluación.

## Ejemplo

Historia sencilla con una alerta de cruce de medias:

1. Llega una vela nueva de `BTC/USDT` en `4h`.
2. Candle recalcula `EMA 9` y `EMA 21`.
3. Comprueba si antes la `EMA 9` estaba por debajo de la `EMA 21` y ahora está por encima.
4. Si eso se cumple, la regla `"EMA Crossover 9/21"` salta.
5. Te llega una alerta con el símbolo, marco temporal, precio y valores relevantes.

## Errores comunes

- Pensar que el bot "adivina" el mercado. No adivina: compara datos con reglas.
- Pensar que una alerta significa certeza. Solo significa que se cumplió una regla.
- Confundir indicador con regla. Un indicador es un dato calculado; una regla es una decisión basada en uno o varios datos.
- Creer que Candle ejecuta operaciones. En este proyecto no lo hace.

---

## El flujo completo como historia

## Explicación simple

El flujo real del proyecto es:

`datos -> indicadores -> condiciones -> reglas -> alerta`

Eso significa:

- `datos`: velas con apertura, máximo, mínimo, cierre y volumen
- `indicadores`: números calculados a partir de esas velas
- `condiciones`: comprobaciones tipo "esto es verdadero o falso"
- `reglas`: conjuntos de condiciones
- `alerta`: aviso final si la regla da `True`

## Qué significa en la práctica

Cada etapa simplifica la anterior:

- Las velas son mucha información.
- Los indicadores la resumen.
- Las condiciones convierten ese resumen en respuestas claras.
- Las reglas te evitan mirar señales sueltas sin contexto.

Si alguna parte falla o falta, la alerta pierde sentido. Por eso conviene leer una alerta sabiendo de qué regla viene.

## Ejemplo

Caso simple:

- Datos: el precio cierra más fuerte y con volumen alto.
- Indicadores: RSI queda en 72 y el precio termina por encima del VWAP.
- Condiciones: `RSI entre 70 y 100` es verdadero, `precio > VWAP` también.
- Regla: si ambas condiciones forman parte de la misma regla, la regla se cumple.
- Alerta: recibes un mensaje diciendo que ese patrón apareció.

## Errores comunes

- Mirar solo el mensaje final y no saber qué regla lo generó.
- Asumir que más indicadores siempre significan mejor señal.
- Olvidar que el marco temporal importa mucho. Una señal en `4h` no significa lo mismo que en `1d`.

---

## Qué hace Candle exactamente

## Explicación simple

En tu proyecto, Candle:

- obtiene velas de exchanges,
- guarda esas velas,
- calcula `EMA 9`, `EMA 21`, `EMA 50`, `EMA 200`, `RSI(14)` y `VWAP`,
- evalúa reglas activas,
- evita repetir la misma alerta durante una ventana de tiempo,
- y envía alertas por Telegram.

No coloca órdenes y no gestiona riesgo por ti.

## Qué significa en la práctica

La alerta es una herramienta para revisar el mercado con menos ruido.

Te ahorra estar mirando gráficos todo el día, pero no te sustituye. Lo útil no es "obedecer" la alerta, sino usarla como un aviso para revisar contexto.

## Ejemplo

Si una misma regla ya saltó hace poco para el mismo par, Candle puede no volver a avisarte de inmediato. Eso evita spam y también evita que reacciones varias veces al mismo evento.

## Errores comunes

- Pensar que si no llega una alerta, no pasa nada en el mercado.
- Pensar que si llegan muchas alertas, todas son igual de importantes.
- Usar Telegram como si fuera una orden automática en lugar de un aviso.
