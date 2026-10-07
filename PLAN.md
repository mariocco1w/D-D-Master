# Plan para las primeras pruebas de D&D Master

El juego descrito en `D&D_proyect_guide.txt` (campañas, DM, bots, fichas, chats y monedas) se construye por capas. La primera capa que ya puede probarse es el catálogo de clases del SRD 5.2.1 y la consulta a un modelo local que solo responde con ese catálogo.

## Estructura

```
dnd_ai/src/dnd_ai/
  config.py              rutas, modelo de embeddings y Ollama
  knowledge/             PDF, parsers (reglas, glosario, clases) e índice Chroma
  classes/               las 12 clases como datos de juego y el texto para el modelo
  llm/                   cliente de Ollama y preguntas sobre clases
dnd_ai/data/json/        clases, reglas y glosario ya parseados
dnd_ai/data/llm/         contexto generado de clases
Learning_master/         PDF del SRD
```

`python -m dnd_ai.knowledge.builder` sigue siendo el constructor del índice vectorial completo. Esa prueba queda para después: el modelo de clases no la necesita.

## Guía Primera clase

Antes de conectar Ollama, quien empieza a jugar tiene la categoría `primera_clase`. No sustituye las reglas: reduce la decisión de hoy a nivel 1 y a tres puertas (delante, astucia, magia). Si la persona no sabe qué elegir, la guía propone el bárbaro. Se lee con `python -m dnd_ai.classes.beginner` y queda escrita en `dnd_ai/data/guides/primera_clase.md`.

## Hecho para la primera prueba

1. El catálogo carga las doce clases y exige característica principal, dado de golpe y una subclase de ejemplo.
2. `python -m dnd_ai.classes` escribe `dnd_ai/data/llm/clases_contexto.md` con el resumen que ve el modelo.
3. `python -m dnd_ai.llm.class_teacher "pregunta"` arma el mensaje:
   - si no nombra clases, adjunta el resumen de las doce;
   - si nombra una o dos, adjunta su ficha con el texto de los rasgos;
   - si nombra tres o más, adjunta solo esos resúmenes.
4. La respuesta sale de Ollama en `http://127.0.0.1:11434`. En este equipo el modelo configurado es `qwen2.5:3b`, con `num_ctx` 4096. `qwen3:4b` queda fuera: no cabe con holgura en 8 GB de RAM.

## Cómo correr las pruebas de clases

Desde `dnd_ai`, con el código en el path:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
python -m dnd_ai.classes
```

Eso comprueba el catálogo y el contexto sin levantar el modelo.

## Este equipo

Revisión del 5 de octubre de 2026: Windows 10 Home, Intel Core i3-7100U (2 núcleos), 7.9 GB de RAM (unos 2 GB libres con los programas abiertos), Intel HD Graphics 620 y 22.9 GB libres en C:. Ollama no está instalado. La gráfica integrada no acelera el modelo: todo el cálculo va por CPU.

`qwen2.5:3b` ocupa cerca de 2 GB y es el modelo del proyecto. Si al abrirlo Windows empieza a usar el disco de intercambio, cierra el navegador o descarga `qwen2.5:1.5b` y arranca la prueba con `$env:DND_OLLAMA_MODEL = "qwen2.5:1.5b"`. No hace falta instalar los dos.

El contexto que viaja a Ollama está recortado a menos de 9000 caracteres para caber en 4096 tokens. El resumen largo de `clases_contexto.md` se queda para leerlo; el chat usa el resumen corto.

## Instalar Ollama

En PowerShell:

```powershell
winget install -e --id Ollama.Ollama
```

Abre Ollama desde el menú Inicio y espera a que aparezca en la bandeja. Luego:

```powershell
ollama pull qwen2.5:3b
```

## Página de pruebas

Desde `dnd_ai`:

```powershell
$env:PYTHONPATH = "src"
python -m dnd_ai.llm.bench
```

Abre `http://127.0.0.1:8765`. La página muestra RAM libre, si Ollama responde y si el modelo está descargado. Cada plan rellena una pregunta. La respuesta tarda alrededor de un minuto en este portátil.

| Plan | Qué recibe Ollama | Cuándo cuenta como bien |
|---|---|---|
| Primera clase | La guía `primera_clase` | Recomienda la clase de la puerta, o al bárbaro si la persona no sabe |
| Clases del SRD | Resumen corto de las clases nombradas, o de las doce | Nombra la clase, su característica y su dado |
| Reglas y glosario | Los fragmentos del glosario y de Cómo jugar que coinciden con la pregunta | Si preguntan por salvación, la respuesta habla de salvación |
| Ficha de nivel 1 | La ficha de hoy de esa clase | Repite clase, característica y dado, sin rasgos posteriores |
| Tirada narrada | El número que ya tiró el programa | Repite ese número y no tira otro |
| Índice del SRD | Aún no se consulta | Falta `data/chroma`. Conviene crearlo con Ollama cerrado |
| Sesión, mesa y monedas | Aún no se consulta | No hay partida guardada. El modelo no debe inventarla |

La consola sigue pudiendo hacer la prueba de clases sin la página:

```powershell
python -m dnd_ai.llm.class_teacher "¿En qué se diferencia un mago de un hechicero?"
```
