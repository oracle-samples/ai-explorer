package org.springframework.ai.openai.samples.helloworld;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.chat.prompt.PromptTemplate;
import org.springframework.ai.document.Document;
import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.ai.reader.ExtractedTextFormatter;
import org.springframework.ai.reader.pdf.PagePdfDocumentReader;
import org.springframework.ai.reader.pdf.config.PdfDocumentReaderConfig;
import org.springframework.ai.transformer.splitter.TokenTextSplitter;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.SimpleVectorStore.Similarity;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.ai.vectorstore.OracleVectorStore;


import jakarta.annotation.PostConstruct;

import org.springframework.core.io.Resource;
import org.springframework.jdbc.core.JdbcTemplate;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.HashMap;

import java.util.Iterator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@RestController
class AIController {

	@Autowired
	private final OracleVectorStore vectorStore;

	@Autowired
	private final EmbeddingModel embeddingModel; 
	
	@Autowired
	private final ChatClient chatClient;

	@Value("${aims.vectortable.name}")
    private String legacyTable;

	@Value("${aims.context_instr}")
    private String contextInstr;

	@Value("${aims.rag_params.search_type}")
	private String searchType;

	@Value("${aims.rag_params.top_k}")
	private int TOPK;

	@Autowired
    private JdbcTemplate jdbcTemplate;

	private static final Logger logger = LoggerFactory.getLogger(AIController.class);
	
	AIController(ChatClient chatClient, EmbeddingModel embeddingModel, OracleVectorStore vectorStore) {

		this.chatClient = chatClient;
		this.embeddingModel = embeddingModel;
		this.vectorStore = vectorStore;

	}

	@GetMapping("/ai")
	Map<String, String> completion(@RequestParam(value = "message", defaultValue = "Tell me a joke") String message) {

			return Map.of(
					"completion",
					chatClient.prompt()
							.user(message)
							.call()
							.content());
	}

	@PostConstruct
	public void insertData() {	
			String sql = "INSERT INTO SPRING_AI_VECTORS (ID, CONTENT, METADATA, EMBEDDING) " +
						 "SELECT ID, TEXT, METADATA, EMBEDDING FROM "+ legacyTable;
			// Execute the insert
			jdbcTemplate.update(sql);
	}
 
	public Prompt promptEngineering(String message, String contextInstr ) {

		String template = """
				DOCUMENTS:
				{documents}

				QUESTION:
				{question}

				INSTRUCTIONS:""";

		String default_Instr ="""
		 		Answer the users question using the DOCUMENTS text above.
				Keep your answer ground in the facts of the DOCUMENTS.
				If the DOCUMENTS doesn’t contain the facts to answer the QUESTION, return:
				I'm sorry but I haven't enough information to answer.
				""";

		template = template + "\n" + contextInstr;

		List<Document> similarDocuments = this.vectorStore.similaritySearch(
				SearchRequest.query(message).withTopK(TOPK));

		StringBuilder context = createContext(similarDocuments);

		PromptTemplate promptTemplate = new PromptTemplate(template);

		Prompt prompt = promptTemplate.create(Map.of("documents", context, "question", message));

		logger.info(prompt.toString());

		return prompt;

	}

	StringBuilder createContext(List<Document> similarDocuments) {
		String START = "\n<article>\n";
		String STOP = "\n</article>\n";

		Iterator<Document> iterator = similarDocuments.iterator();
		StringBuilder context = new StringBuilder();
		while (iterator.hasNext()) {
			Document document = iterator.next();
			context.append(document.getId() + ".");
			context.append(START + document.getFormattedContent() + STOP);
		}
		return context;
	}

	@GetMapping("/rag")
	Map<String, String> completionRag(@RequestParam(value = "message", defaultValue = "Tell me a joke") String message) {

		Prompt prompt = promptEngineering(message,contextInstr);
		logger.info(prompt.getContents());

		return Map.of(
				"completion",
				chatClient.prompt(prompt)
						.call()
						.content());
	}

	@GetMapping("/search")
	List<Map<String, Object>> search(@RequestParam(value = "message", defaultValue = "Tell me a joke") String query, @RequestParam(value = "topk", defaultValue = "5" ) Integer topK) {
		
		List<Document> similarDocs = vectorStore.similaritySearch(SearchRequest.defaults()
		.withQuery(query)
		.withTopK(topK));

		List<Map<String, Object>> resultList = new ArrayList<>();
		for (Document d : similarDocs) {
            Map<String, Object> metadata = d.getMetadata();
            Map doc = new HashMap<>();
            doc.put("id", d.getId());
            resultList.add(doc);
        };
        return resultList;
	}
}
