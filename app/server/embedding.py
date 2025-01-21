"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore langchain, docstore, docos, getbuffer, tiktoken, vectorstores, oraclevs, genai

import json
import copy
import math
import os
import time
from typing import List, Union

import bs4
import oracledb

# Langchain
import langchain_community.document_loaders as document_loaders
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import oraclevs as LangchainVS
from langchain_community.vectorstores.oraclevs import OracleVS
from langchain_core.language_models.chat_models import BaseChatModel
from langchain.docstore.document import Document as LangchainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_text_splitters import HTMLSectionSplitter, CharacterTextSplitter

import server.databases as databases

import common.functions
import common.schema as schema

import common.logging_config as logging_config

logger = logging_config.logging.getLogger("server.embedding")


def drop_vs(conn: oracledb.Connection, vs: schema.DatabaseVectorStorage) -> None:
    """Drop Vector Storage"""
    logger.info("Dropping Vector Store: %s", vs.vector_store)
    LangchainVS.drop_table_purge(conn, vs.vector_store)


def get_vs(conn: oracledb.Connection) -> schema.DatabaseVectorStorage:
    """Retrieve Vector Storage Tables"""
    logger.info("Looking for Vector Storage Tables")
    vector_stores = []
    sql = """SELECT ut.table_name,
                    REPLACE(utc.comments, 'GENAI: ', '') AS comments
                FROM all_tab_comments utc, all_tables ut
                WHERE utc.table_name = ut.table_name
                AND utc.comments LIKE 'GENAI:%'"""
    results = databases.execute_sql(conn, sql)
    for table_name, comments in results:
        comments_dict = json.loads(comments)
        vector_stores.append(schema.DatabaseVectorStorage(vector_store=table_name, **comments_dict))

    return vector_stores


def doc_to_json(document: LangchainDocument, file: str, output_dir: str = None) -> List:
    """Creates a JSON file of the Document.  Returns the json file destination"""
    src_file_name = os.path.basename(file)
    dst_file_name = "_" + os.path.splitext(src_file_name)[0] + ".json"

    docs_dict = [doc.to_json() for doc in document]
    json_data = json.dumps(docs_dict, indent=4)

    dst_file_path = os.path.join(output_dir, dst_file_name)
    with open(dst_file_path, "w", encoding="utf-8") as file:
        file.write(json_data)
    file_size = os.path.getsize(dst_file_path)
    logger.info("Wrote split JSON file: %s (%i bytes)", dst_file_path, file_size)

    return dst_file_path


def process_metadata(idx, chunk):
    """Add Metadata to Split Document"""
    filename = os.path.basename(chunk.metadata["source"])
    file = os.path.splitext(filename)[0]

    split_doc_with_mdata = []
    chunk_metadata = chunk.metadata.copy()
    # Add More Metadata as Required
    chunk_metadata["id"] = f"{file}_{idx}"
    chunk_metadata["filename"] = filename
    split_doc_with_mdata.append(LangchainDocument(page_content=str(chunk.page_content), metadata=chunk_metadata))
    return split_doc_with_mdata


def split_document(
    model: str,
    chunk_size: int,
    chunk_overlap: int,
    document: List[LangchainDocument],
    extension: str,
) -> List[LangchainDocument]:
    """
    Split documents into chunks of size `chunk_size` characters and return a list of documents.
    """
    ##################################
    # Splitters - Start
    ##################################
    logger.info("Splitting for %s", model)
    chunk_overlap_ceil = math.ceil(chunk_overlap)
    match model:
        case "text-embedding*":
            text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
                separator="\n\n",
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap_ceil,
                is_separator_regex=False,
                model_name=model,
                encoding_name=model,
            )
        case _:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap_ceil,
                add_start_index=True,
                strip_whitespace=True,
                length_function=len,
            )
    ## HTML
    headers_to_split_on = [
        ("h1", "Header 1"),
        ("h2", "Header 2"),
        ("h3", "Header 3"),
        ("h4", "Header 4"),
        ("h5", "Header 5"),
    ]
    html_splitter = HTMLSectionSplitter(headers_to_split_on=headers_to_split_on)
    ##################################
    # Splitters - End
    ##################################
    match extension.lower():
        case "pdf":
            doc_split = text_splitter.split_documents(document)
        case "html":
            try:
                html_split = html_splitter.split_documents(document)
            except Exception as ex:
                logger.exception(ex)
                html_split = document
            doc_split = text_splitter.split_documents(html_split)
        case "md":
            doc_split = text_splitter.split_documents(document)
        case "csv":
            doc_split = text_splitter.split_documents(document)

    logger.info("Number of Chunks: %i", len(doc_split))
    return doc_split


##########################################
# Documents
##########################################
def load_and_split_documents(
    src_files: List,
    model: str,
    chunk_size: int,
    chunk_overlap: int,
    write_json: bool = False,
    output_dir: str = None,
) -> List[LangchainDocument]:
    """
    Loads file into a Langchain Document.  Calls the Splitter (split_document) function
    Returns the list of the chunks in a LangchainDocument.
    If output_dir, a list of written json files
    """
    split_files = []
    all_split_docos = []
    for file in src_files:
        name = os.path.basename(file)
        stat = os.stat(file)
        extension = os.path.splitext(file)[1][1:]
        logger.info("Loading %s (%i bytes)", name, stat.st_size)
        match extension.lower():
            case "pdf":
                loader = document_loaders.PyPDFLoader(file)
            case "html":
                loader = document_loaders.UnstructuredHTMLLoader(file)
            case "md":
                loader = document_loaders.TextLoader(file)
            case "csv":
                loader = document_loaders.CSVLoader(file)
            case _:
                raise ValueError(f"{extension} is not a supported file extension")

        loaded_doc = loader.load()
        logger.info("Loaded Pages: %i", len(loaded_doc))

        # Chunk the File
        split_doc = split_document(model, chunk_size, chunk_overlap, loaded_doc, extension)

        # Add IDs to metadata
        split_docos = []
        for idx, chunk in enumerate(split_doc, start=1):
            split_doc_with_mdata = process_metadata(idx, chunk)
            split_docos += split_doc_with_mdata

        if write_json and output_dir:
            split_files.append(doc_to_json(split_docos, file, output_dir))
        all_split_docos += split_docos
    logger.info("Total Number of Chunks: %i", len(all_split_docos))

    return all_split_docos, split_files


##########################################
# Web
##########################################
def load_and_split_url(
    model: str,
    url: str,
    chunk_size: int,
    chunk_overlap: int,
) -> List[LangchainDocument]:
    """
    Loads URL into a Langchain Document.  Calls the Splitter (split_document) function
    Returns the list of the chunks in a LangchainDocument.
    If output_dir, a list of written json files
    """
    split_docos = []
    split_files = []

    logger.info("Loading %s", url)
    loader = WebBaseLoader(
        web_paths=(f"{url}",),
        bs_kwargs=dict(parse_only=bs4.SoupStrainer()),
    )

    loaded_doc = loader.load()
    logger.info("Document Size: %s bytes", str(loaded_doc.__sizeof__()))
    logger.info("Loaded Pages: %i", len(loaded_doc))

    # Chunk the File
    split_doc = split_document(model, chunk_size, chunk_overlap, loaded_doc, "html")

    # Add IDs to metadata
    for idx, chunk in enumerate(split_doc, start=1):
        split_doc_with_mdata = process_metadata(idx, chunk)
        split_docos += split_doc_with_mdata

    logger.info("Total Number of Chunks: %i", len(split_docos))
    if len(split_docos) == 0:
        raise ValueError("Input source contains no chunk-able data.")

    return split_docos, split_files


##########################################
# Vector Store
##########################################
def populate_vs(
    vector_store: schema.DatabaseVectorStorage,
    db_conn: oracledb.Connection,
    embed_client: BaseChatModel,
    input_data: Union[List["LangchainDocument"], List] = None,
    rate_limit: int = 0,
) -> None:
    """Populate the Vector Storage"""
    # Copy our vector storage object so can process a tmp one
    vector_store_tmp = copy.copy(vector_store)
    vector_store_tmp.vector_store = f"{vector_store.vector_store}_TMP"

    def json_to_doc(file: str):
        """Creates a list of LangchainDocument from a JSON file. Returns the list of documents."""
        logger.info("Converting %s to Document", file)

        with open(file, "r", encoding="utf-8") as document:
            chunks = json.load(document)
            docs = []
            for chunk in chunks:
                page_content = chunk["kwargs"]["page_content"]
                metadata = chunk["kwargs"]["metadata"]
                docs.append(LangchainDocument(page_content=str(page_content), metadata=metadata))

        logger.info("Total Chunk Size: %i bytes", docs.__sizeof__())
        logger.info("Chunks ingested: %i", len(docs))
        return docs

    # Loop through files and create Documents
    if isinstance(input_data[0], LangchainDocument):
        logger.debug("Processing Documents: %s", input_data)
        documents = input_data
    else:
        documents = []
        for file in input_data:
            logger.info("Processing file: %s into a Document.", file)
            documents.extend(json_to_doc(file))

    logger.info("Size of Payload: %i bytes", documents.__sizeof__())
    logger.info("Total Chunks: %i", len(documents))

    # Remove duplicates (copy-writes, etc)
    unique_texts = {}
    unique_chunks = []
    for chunk in documents:
        if chunk.page_content not in unique_texts:
            unique_texts[chunk.page_content] = True
            unique_chunks.append(chunk)
    logger.info("Total Unique Chunks: %i", len(unique_chunks))

    # Creates a TEMP Vector Store Table; which may already exist
    # This is to allow re-using an existing VS; will merge this over later
    # drop_vs(conn=db_conn, vs=vector_store_tmp) -- THIS SEEMS TO HANG
    vs_tmp = OracleVS(
        client=db_conn,
        embedding_function=embed_client,
        table_name=vector_store_tmp.vector_store,
        distance_strategy=vector_store.distance_metric,
    )

    # Batch Size does not have a measurable impact on performance
    # but does eliminate issues with timeouts
    # Careful increasing as may break token rate limits
    batch_size = 500
    for i in range(0, len(unique_chunks), batch_size):
        batch = unique_chunks[i : i + batch_size]
        logger.info(
            "Processing: %i Chunks of %i (Rate Limit: %i)",
            len(unique_chunks) if len(unique_chunks) < i + batch_size else i + batch_size,
            len(unique_chunks),
            rate_limit,
        )
        OracleVS.add_documents(vs_tmp, documents=batch)
        if rate_limit > 0:
            interval = 60 / rate_limit
            logger.info("Rate Limiting: sleeping for %i seconds", interval)
            time.sleep(interval)

    # Create our real vector storage if doesn't exist
    vs_real = OracleVS(
        client=db_conn,
        embedding_function=embed_client,
        table_name=vector_store.vector_store,
        distance_strategy=vector_store.distance_metric,
    )
    vector_store_idx = f"{vector_store.vector_store}_IDX"
    if vector_store.index_type == "HNSW":
        LangchainVS.drop_index_if_exists(db_conn, vector_store_idx)

    # Perform the Merge
    merge_sql = f"""
        INSERT INTO {vector_store.vector_store} SELECT * FROM {vector_store_tmp.vector_store} src 
         WHERE NOT EXISTS (SELECT 1 FROM {vector_store.vector_store} tgt WHERE tgt.ID = src.ID)
    """
    logger.info("Merging %s into %s", vector_store_tmp.vector_store, vector_store.vector_store)
    databases.execute_sql(db_conn, merge_sql)
    drop_vs(conn=db_conn, vs=vector_store_tmp)

    # Build the Index
    logger.info("Creating index on: %s", vector_store.vector_store)
    try:
        index_type = vector_store.index_type
        params = {"idx_name": vector_store_idx, "idx_type": index_type}
        LangchainVS.create_index(db_conn, vs_real, params)
    except Exception as ex:
        logger.error("Unable to create vector index: %s", ex)

    # Comment the VS table
    _, store_comment = common.functions.get_vs_table(**vector_store.model_dump(exclude={"database", "vector_store"}))
    comment = f"COMMENT ON TABLE {vector_store.vector_store} IS 'GENAI: {store_comment}'"
    databases.execute_sql(db_conn, comment)
