"""Módulo para el almacén vectorial persistent en ChromaDB."""
from __future__ import annotations

import json
from typing import Any

import chromadb

from .config import CHROMA_DIR, JSON_DIR, CHUNK_OVERLAP, CHUNK_SIZE, ensure_dirs
from .embeddings import MultilingualEmbeddingFunction
from .parsers.common import chunk_text, slugify

COLLECTION_NAME = "srd_5_2_knowledge"


def get_chroma_client() -> chromadb.PersistentClient:
    ensure_dirs()
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_or_create_collection(
    client: chromadb.PersistentClient | None = None,
) -> chromadb.Collection:
    if client is None:
        client = get_chroma_client()
    embedding_fn = MultilingualEmbeddingFunction()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "Conocimiento del SRD 5.2.1 de D&D (reglas, glosario, clases)"},
    )


def build_vector_store() -> int:
    """Lee los archivos JSON parseados, genera los chunks e indexa en ChromaDB."""
    ensure_dirs()
    client = get_chroma_client()

    # Recrear la colección para indexado limpio
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = get_or_create_collection(client)

    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []
    ids: list[str] = []

    # 1. Glosario
    glosario_path = JSON_DIR / "glosario.json"
    if glosario_path.exists():
        entries = json.loads(glosario_path.read_text(encoding="utf-8"))
        for e in entries:
            doc_text = f"{e['termino']}: {e['definicion']}"
            documents.append(doc_text)
            metadatas.append(
                {
                    "fuente": "glosario",
                    "titulo": e["termino"],
                    "tag": e["tag"] or "",
                    "cita": f"SRD 5.2.1 Glosario: '{e['termino']}'",
                }
            )
            ids.append(f"vec-{e['id']}")

    # 2. Reglas
    reglas_path = JSON_DIR / "reglas.json"
    if reglas_path.exists():
        sections = json.loads(reglas_path.read_text(encoding="utf-8"))
        for s in sections:
            text = s["contenido"]
            chunks = chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
            for idx, c_text in enumerate(chunks):
                doc_text = f"Regla [{s['capitulo']} - {s['seccion']}]: {c_text}"
                documents.append(doc_text)
                metadatas.append(
                    {
                        "fuente": "reglas",
                        "capitulo": s["capitulo"],
                        "seccion": s["seccion"],
                        "pagina": s["pagina"],
                        "cita": f"SRD 5.2.1 Cómo jugar, p. {s['pagina']} ('{s['seccion']}')",
                    }
                )
                ids.append(f"vec-{s['id']}-{idx}")

    # 3. Clases
    clases_path = JSON_DIR / "clases.json"
    if clases_path.exists():
        classes = json.loads(clases_path.read_text(encoding="utf-8"))
        for c in classes:
            c_name = c["clase"]
            for s in c["secciones"]:
                t_type = s["tipo"]
                if t_type == "atributos":
                    meta_lines = [f"{k}: {v}" for k, v in s.get("metadatos", {}).items()]
                    raw_text = "\n".join(meta_lines)
                else:
                    raw_text = s.get("contenido", "")
                if not raw_text:
                    continue

                chunks = chunk_text(raw_text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
                for idx, c_text in enumerate(chunks):
                    doc_text = f"Clase {c_name} [{s['titulo']}]: {c_text}"
                    documents.append(doc_text)
                    metadatas.append(
                        {
                            "fuente": "clases",
                            "clase": c_name,
                            "titulo": s["titulo"],
                            "tipo": t_type,
                            "cita": f"SRD 5.2.1 Clases: {c_name} ('{s['titulo']}')",
                        }
                    )
                    ids.append(f"vec-clase-{slugify(c_name)}-{slugify(s['titulo'])}-{idx}")

    # Insertar en lotes de 100
    batch_size = 100
    total = len(documents)
    for i in range(0, total, batch_size):
        end = min(i + batch_size, total)
        collection.add(
            documents=documents[i:end],
            metadatas=metadatas[i:end],
            ids=ids[i:end],
        )

    print(f"[store] Indexados {total} vectores en ChromaDB ('{COLLECTION_NAME}')")
    return total


def search_knowledge(
    query: str, n_results: int = 4, fuente_filter: str | None = None
) -> list[dict[str, Any]]:
    """Busca en el almacén vectorial y devuelve los resultados formateados."""
    collection = get_or_create_collection()
    where = {"fuente": fuente_filter} if fuente_filter else None
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where,
    )

    out: list[dict[str, Any]] = []
    if results and results["documents"] and results["documents"][0]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
        dists = results["distances"][0] if results["distances"] else [0.0] * len(docs)
        for doc, meta, dist in zip(docs, metas, dists):
            out.append(
                {
                    "documento": doc,
                    "metadata": meta,
                    "distancia": dist,
                }
            )
    return out


if __name__ == "__main__":
    n = build_vector_store()
    print("Prueba de búsqueda:")
    res = search_knowledge("¿Cómo funciona el ataque de oportunidad?", n_results=2)
    for r in res:
        print(f" -> {r['metadata'].get('cita')}: {r['documento'][:100]}...")
