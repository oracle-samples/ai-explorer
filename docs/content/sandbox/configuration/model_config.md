+++
title = '🤖 Model Configuration'
weight = 10
+++
<!--
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
-->
<!-- spell-checker:ignore ollama, mxbai, nomic, thenlper, minilm, uniqueid, huggingface, hftei, openai, pplx -->

## Supported Models

At a minimum, a Large _Language Model_ (LLM) must be configured in **Oracle AI Microservices Sandbox** for basic functionality. For Retrieval-Augmented Generation (**RAG**), an _Embedding Model_ will also need to be configured.

{{% notice style="default" title="10-Sept-2024: Documentation In-Progress..." icon="pen" %}}
If there is a specific model that you would like to use with the **Oracle AI Microservices Sandbox**, please [open an issue in GitHub](https://github.com/oracle-samples/oaim-sandbox/issues/new).
{{% /notice %}}

| Model                           | Type  | API                                                      | On-Premises |
| ------------------------------- | ----- | -------------------------------------------------------- | ----------- |
| llama3.1                        | LLM   | [ChatOllama](#additional-information)                    | X           |
| gpt-3.5-turbo                   | LLM   | [OpenAI](#additional-information)                        |             |
| gpt-4o-mini                     | LLM   | [OpenAI](#additional-information)                        |             |
| gpt-4                           | LLM   | [OpenAI](#additional-information)                        |             |
| gpt-4o                          | LLM   | [OpenAI](#additional-information)                        |             |
| llama-3-sonar-small-128k-chat   | LLM   | [ChatPerplexity](#additional-information)                |             |
| llama-3-sonar-small-128k-online | LLM   | [ChatPerplexity](#additional-information)                |             |
| command-r                       | LLM   | [Cohere](#additional-information)                        |             |
| mxbai-embed-large               | Embed | [OllamaEmbeddings](#additional-information)              |             |
| nomic-embed-text                | Embed | [OllamaEmbeddings](#additional-information)              | X           |
| all-minilm                      | Embed | [OllamaEmbeddings](#additional-information)              | X           |
| thenlper/gte-base               | Embed | [HuggingFaceEndpointEmbeddings](#additional-information) | X           |
| text-embedding-3-small          | Embed | [OpenAIEmbeddings](#additional-information)              |             |
| text-embedding-3-large          | Embed | [OpenAIEmbeddings](#additional-information)              |             |
| embed-english-v3.0              | Embed | [CohereEmbeddings](#additional-information)              |             |
| embed-english-light-v3.0        | Embed | [CohereEmbeddings](#additional-information)              |             |


## Configuration

The models can either be configured using environment variables or through the **Sandbox** interface. To configure models through environment variables, please read the [Additional Information](#additional-information) about the specific model you would like to configure.

To configure an LLM or embedding model from the **Sandbox**, navigate to `Configuration -> Models`:

![Model Config](../images/model_config.png)

Here you can configure both Large _Language Models_ and _Embedding Models_. Set the API Keys and API URL as required. You can also Enable and Disable models.

### API Keys

Third-Party cloud models, such as [OpenAI](https://openai.com/api/) and [Perplexity AI](https://docs.perplexity.ai/getting-started), require API Keys. These keys are tied to registered, funded accounts on these platforms. For more information on creating an account, funding it, and generating API Keys for third-party cloud models, please visit their respective sites.

![Cloud Model API Keys](../images/model_third-party-api-key.png)

On-Premises models, such as those from [Ollama](https://ollama.com/) or [HuggingFace](https://huggingface.co/) usually do not require API Keys. These values can be left blank.

![On-Premises Model API Keys](../images/model_on-prem-api-key.png)

### API URL

When using an on-premises model, for performance purposes, they should be running on hosts with GPUs. As the **Sandbox** does not require GPUs, often is the case that the API URL for these models will be the IP or hostname address of a remote host. Specify the API URL and Port of the remote host.

![On-Premises Model API URL](../images/model_on-prem-api-url.png)

## Additional Information

{{< tabs "uniqueid" >}}
{{% tab title="Ollama" %}}
# Ollama

[Ollama](https://ollama.com/) is an open-source project that simplifies the running of LLMs and Embedding Models On-Premises.

When configuring an Ollama model in the **Sandbox**, set the `API Server` URL (e.g `http://127.0.0.1:11434`) and leave the API Key blank. Substitute the IP Address with the IP of where Ollama is running.

>[!code]Skip the GUI!
>You can set the following environment variable to automatically set the `API Server` URL and enable Ollama models (change the IP address and Port, as applicable to your environment):
>```shell
>export ON_PREM_OLLAMA_URL=http://127.0.0.1:11434
>```

## Quick-start

Example of running llama3.1 on a Linux host:

1. Install Ollama:

```shell
sudo curl -fsSL https://ollama.com/install.sh | sh
```

1. Pull the llama3.1 model:

```shell
ollama pull llama3.1
```

1. Start Ollama

```shell
ollama serve
```

For more information and instructions on running Ollama on other platforms, please visit the [Ollama GitHub Repository](https://github.com/ollama/ollama/blob/main/README.md#quickstart).

{{% /tab %}}
{{% tab title="HuggingFace" %}}
# HuggingFace

[HuggingFace](https://huggingface.co/) is a platform where the machine learning community collaborates on models, datasets, and applications. It provides a large selection of models that can be run both in the cloud and On-Premises.

>[!code]Skip the GUI!
>You can set the following environment variable to automatically set the `API Server` URL and enable HuggingFace models (change the IP address and Port, as applicable to your environment):
:
>```shell
>export ON_PREM_HF_URL=http://127.0.0.1:8080
>```

## Quick-start

Example of running thenlper/gte-base in a container:

1. Set the Model based on CPU or GPU

   For CPUs: `export HF_IMAGE=ghcr.io/huggingface/text-embeddings-inference:cpu-1.2`
   For GPUs: `export HF_IMAGE=ghcr.io/huggingface/text-embeddings-inference:0.6`

1. Define a Temporary Volume

   ```bash
   export TMP_VOLUME=/tmp/hf_data
   mkdir -p $TMP_VOLUME
   ```

1. Define the Model

   ```bash
   export HF_MODEL=thenlper/gte-base
   ```

1. Start the Container

   ```bash
   podman run -d -p 8080:80 -v $TMP_VOLUME:/data --name hftei-gte-base \
       --pull always ${image} --model-id $HF_MODEL --max-client-batch-size 5024
   ```

1. Determine the IP

   ```bash
   docker inspect hftei-gte-base | grep IPA
   ```

   **NOTE:** if there is no IP, use 127.0.0.1
{{% /tab %}}
{{% tab title="Cohere" %}}
# Cohere

[Cohere](https://cohere.com/) is an AI-powered answer engine. To use Cohere, you will need to sign-up and provide the **Sandbox** an API Key.  Cohere offers a free-trial, rate-limited API Key.

**WARNING:** Cohere is a cloud model and you should familiarize yourself with their Privacy Policies if using it to experiment with private, sensitive data in the **Sandbox**.

>[!code]Skip the GUI!
>You can set the following environment variable to automatically set the `API Key` and enable Perplexity models:
:
>```shell
>export COHERE_API_KEY=<super-secret API Key>
>```
{{% /tab %}}
{{% tab title="OpenAI" %}}
# OpenAI

[OpenAI](https://openai.com/api/) is an AI research organization behind the popular, online ChatGPT chatbot. To use OpenAI models, you will need to sign-up, purchase credits, and provide the **Sandbox** an API Key.

**WARNING:** OpenAI is a cloud model and you should familiarize yourself with their Privacy Policies if using it to experiment with private, sensitive data in the **Sandbox**.

>[!code]Skip the GUI!
>You can set the following environment variable to automatically set the `API Key` and enable OpenAI models:
:
>```shell
>export OPENAI_API_KEY=<super-secret API Key>
>```

{{% /tab %}}
{{% tab title="Perplexity AI" %}}
# Perplexity AI

[Perplexity AI](https://docs.perplexity.ai/getting-started) is an AI-powered answer engine. To use Perplexity AI models, you will need to sign-up, purchase credits, and provide the **Sandbox** an API Key.

**WARNING:** Perplexity AI is a cloud model and you should familiarize yourself with their Privacy Policies if using it to experiment with private, sensitive data in the **Sandbox**.

>[!code]Skip the GUI!
>You can set the following environment variable to automatically set the `API Key` and enable Perplexity models:
:
>```shell
>export PPLX_API_KEY=<super-secret API Key>
>```
{{% /tab %}}
{{< /tabs >}}
