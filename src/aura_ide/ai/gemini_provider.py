import google.generativeai as genai
from .base_provider import BaseAIProvider

# Modelos Gemini comuns.
# O modelo exato pode depender da sua chave e dos modelos disponíveis para ela.
# 'gemini-pro' é um bom ponto de partida para chat.
# 'gemini-1.5-flash-latest' é mais rápido e mais barato, 'gemini-1.5-pro-latest' é mais capaz.
# Para este exemplo, vamos permitir que o usuário escolha ou usar um padrão.
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash-latest"

class GeminiProvider(BaseAIProvider):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API Key para Gemini não fornecida.")
        try:
            genai.configure(api_key=api_key)
            # Teste rápido para ver se a configuração funcionou (opcional, mas bom)
            # Tentaremos listar modelos para verificar a chave indiretamente.
            self.available_models_list = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if not self.available_models_list: # Se a lista estiver vazia após o filtro
                raise Exception("Nenhum modelo Gemini adequado (com generateContent) encontrado ou chave inválida.")
            print(f"Modelos Gemini disponíveis (com generateContent): {self.available_models_list}")

        except Exception as e:
            print(f"Erro ao configurar a API Gemini ou listar modelos: {e}")
            # Re-levantar a exceção para que a MainWindow possa tratá-la
            raise ValueError(f"Falha na configuração do GeminiProvider: {e}") from e


    def get_chat_completion(self, messages: list, model_name: str = None) -> str:
        """
        Obtém uma completude de chat da API Gemini.
        A API do Gemini espera um histórico de chat um pouco diferente (sem 'system' role diretamente no chat).
        A mensagem de sistema pode ser passada como `system_instruction` no `GenerativeModel`.
        """
        selected_model_name = model_name if model_name else DEFAULT_GEMINI_MODEL
        
        # A API Gemini espera 'parts' dentro de 'content' e usa 'user' e 'model' para roles.
        # A mensagem de 'system' pode ser tratada como instrução do modelo.
        system_instruction_content = None
        gemini_chat_history = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role == "system":
                system_instruction_content = content # Captura a última instrução de sistema
            elif role == "user":
                gemini_chat_history.append({'role': 'user', 'parts': [content]})
            elif role == "assistant": # A API Gemini usa 'model' para as respostas do assistente
                gemini_chat_history.append({'role': 'model', 'parts': [content]})
        
        try:
            # Adicionar "models/" ao nome do modelo se não estiver presente, pois a API do genai espera.
            if not selected_model_name.startswith("models/"):
                api_model_name_formatted = f"models/{selected_model_name}"
            else:
                api_model_name_formatted = selected_model_name

            # Verificar se o modelo formatado está realmente na lista de modelos disponíveis
            # Isto é uma checagem extra, já que list_models() já filtrou.
            if selected_model_name not in self.available_models_list: # Checa contra o nome limpo
                 return f"Erro: Modelo Gemini '{selected_model_name}' não está entre os disponíveis ou adequados."


            model_args = {}
            if system_instruction_content:
                model_args["system_instruction"] = system_instruction_content
            
            model = genai.GenerativeModel(api_model_name_formatted, **model_args)

            # Se houver histórico, podemos iniciar um chat para manter o contexto.
            # Se for uma única pergunta (última mensagem é do usuário), podemos usar generate_content diretamente.
            # Para simplificar, vamos tratar a última mensagem como o prompt atual, e o resto como histórico.
            
            if not gemini_chat_history or gemini_chat_history[-1]['role'] != 'user':
                return "Erro: A última mensagem para Gemini deve ser do usuário."

            current_prompt_parts = gemini_chat_history.pop()['parts'] # Pega a última mensagem do usuário

            if gemini_chat_history: # Se houver histórico anterior
                chat_session = model.start_chat(history=gemini_chat_history)
                response = chat_session.send_message(current_prompt_parts)
            else: # Sem histórico anterior, apenas um prompt
                response = model.generate_content(current_prompt_parts)

            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text.strip()
            elif response.prompt_feedback and response.prompt_feedback.block_reason:
                return f"Resposta bloqueada pela API Gemini: {response.prompt_feedback.block_reason_message}"
            else:
                # Tentar obter o texto mesmo que a estrutura não seja a esperada
                try:
                    return response.text.strip()
                except AttributeError:
                    print(f"Resposta inesperada ou vazia da API Gemini: {response}")
                    return "Erro: Resposta inesperada ou vazia da API Gemini."

        except Exception as e:
            print(f"Erro ao chamar a API Gemini: {e}")
            # Tentar extrair mais detalhes se for um erro da API do Google
            if hasattr(e, 'message'): # Muitos erros da API Google têm um atributo 'message'
                return f"Erro na API Gemini: {e.message}"
            return f"Erro ao comunicar com a API Gemini: {e}"

    def get_available_models(self) -> list:
        """
        Retorna os nomes dos modelos Gemini que suportam 'generateContent'.
        """
        return self.available_models_list[:] # Retorna uma cópia
    
    # Dentro da classe GeminiProvider em gemini_provider.py
    def get_default_model_name(self) -> str:
        return DEFAULT_GEMINI_MODEL