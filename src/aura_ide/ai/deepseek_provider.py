import requests # Certifique-se de que 'requests' está no seu requirements.txt e instalado
import json
from .base_provider import BaseAIProvider

# Constantes para a API DeepSeek
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_DEEPSEEK_MODEL = "deepseek-coder" # Modelo focado em código

class DeepSeekProvider(BaseAIProvider):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API Key para DeepSeek não fornecida.")
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def get_chat_completion(self, messages: list, model_name: str = None) -> str:
        """
        Obtém uma completude de chat da API DeepSeek.
        """
        selected_model = model_name if model_name else DEFAULT_DEEPSEEK_MODEL

        payload = {
            "model": selected_model,
            "messages": messages,
            # Você pode adicionar outros parâmetros aqui, como:
            # "temperature": 0.7,
            # "max_tokens": 2048,
            # "stream": False # Para respostas de streaming, precisaríamos de lógica diferente
        }

        try:
            response = requests.post(DEEPSEEK_API_URL, headers=self.headers, json=payload, timeout=30) # Timeout de 30s
            response.raise_for_status()  # Levanta HTTPError para respostas de erro (4xx ou 5xx)

            response_data = response.json()

            if response_data.get("choices") and len(response_data["choices"]) > 0:
                ai_message = response_data["choices"][0].get("message", {}).get("content")
                if ai_message:
                    return ai_message.strip()
                else:
                    return "Erro: Resposta da IA não continha conteúdo de mensagem."
            else:
                # Log detalhado da resposta pode ser útil aqui
                print(f"Resposta inesperada da API DeepSeek: {response_data}")
                return "Erro: Formato de resposta inesperado da API DeepSeek."

        except requests.exceptions.HTTPError as http_err:
            # Tentar obter mais detalhes do corpo da resposta se for um erro da API
            error_details = ""
            try:
                error_data = response.json()
                error_details = error_data.get("error", {}).get("message", "")
            except json.JSONDecodeError:
                error_details = response.text # Se não for JSON
            
            print(f"Erro HTTP da API DeepSeek: {http_err} - Detalhes: {error_details}")
            return f"Erro na API DeepSeek: {http_err.response.status_code} - {error_details if error_details else http_err.response.reason}"
        except requests.exceptions.RequestException as req_err:
            print(f"Erro de requisição para API DeepSeek: {req_err}")
            return f"Erro de conexão com a API DeepSeek: {req_err}"
        except Exception as e:
            print(f"Erro inesperado ao processar resposta da DeepSeek: {e}")
            return f"Erro inesperado: {e}"

    def get_available_models(self) -> list:
        """
        Retorna uma lista de modelos DeepSeek Coder (e outros de chat se aplicável).
        Para este exemplo, vamos retornar o padrão.
        Em uma implementação real, poderíamos consultar um endpoint ou ter uma lista fixa.
        """
        return [DEFAULT_DEEPSEEK_MODEL, "deepseek-chat"] # Adicionando outro modelo de exemplo