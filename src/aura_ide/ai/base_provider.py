from abc import ABC, abstractmethod

class BaseAIProvider(ABC):
    """
    Classe base abstrata para provedores de serviços de IA.
    Define a interface que todos os provedores de IA devem implementar.
    """

    @abstractmethod
    def get_chat_completion(self, messages: list, model_name: str = None) -> str:
        """
        Obtém uma completude de chat a partir de uma lista de mensagens.

        Args:
            messages (list): Uma lista de dicionários, onde cada dicionário
                             representa uma mensagem no formato:
                             {'role': 'user'/'assistant'/'system', 'content': 'texto da mensagem'}
            model_name (str, optional): O nome específico do modelo a ser usado,
                                        se o provedor suportar múltiplos.

        Returns:
            str: A resposta de texto do modelo de IA.

        Raises:
            NotImplementedError: Se o método não for implementado pela subclasse.
            Exception: Pode levantar exceções específicas do provedor em caso de erro na API.
        """
        pass

    @abstractmethod
    def get_available_models(self) -> list:
        """
        Retorna uma lista de nomes de modelos de chat disponíveis suportados por este provedor.

        Returns:
            list: Uma lista de strings com os nomes dos modelos.
        """
        pass

# Você pode adicionar mais métodos abstratos aqui no futuro,
# por exemplo, para embeddings, geração de imagem, etc., conforme necessário.