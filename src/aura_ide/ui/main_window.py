import sys
import configparser
from aura_ide.ai.gemini_provider import GeminiProvider
from aura_ide.ui.widgets.ai_terminal_widget import AITerminalWidget

# Se BaseAIProvider for usado para type hinting:
# from aura_ide.ai.base_provider import BaseAIProvider

from PySide6.QtCore import Qt, QDir, QTimer 
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QSplitter,
    QTreeView,
    QFileSystemModel,
    QHeaderView,
    QPlainTextEdit,
    QComboBox,
    QLineEdit,
    QPushButton
)
from aura_ide.ui.widgets.simple_terminal import SimpleTerminal # Importação adicionada
from aura_ide.ui.widgets.chat_input_text_edit import ChatInputTextEdit # Nova importação

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Aura IDE - Protótipo")
        self.setGeometry(100, 100, 1024, 768) # Configurações básicas primeiro

        # 1. Criar os componentes da UI (menus, layout principal com todos os widgets)
        self._create_menu_bar()
        self._create_main_layout() # Agora self.ai_model_selector e self.chat_display_area existem

        # 2. Inicializar o provedor de IA e carregar configurações
        #    Agora é seguro chamar este método, pois os widgets da UI que ele usa já existem.
        self.ai_provider = None 
        self._load_config_and_init_ai()
        
        # Outras inicializações que dependam da UI ou da IA podem vir aqui

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        # Menu Arquivo (existente)
        file_menu = menu_bar.addMenu("&Arquivo")
        # ... (ações existentes do menu Arquivo) ...
        new_action = file_menu.addAction("Novo")
        open_action = file_menu.addAction("Abrir")
        save_action = file_menu.addAction("Salvar")
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Sair")
        exit_action.triggered.connect(self.close)

        # Menu Editar (existente)
        edit_menu = menu_bar.addMenu("&Editar")
        # ... (ações existentes do menu Editar) ...
        edit_menu.addAction("Copiar")
        edit_menu.addAction("Colar")

        # NOVO: Menu Controle da IA
        ia_control_menu = menu_bar.addMenu("&IA Controle")

        self.pause_ia_editor_action = ia_control_menu.addAction("Pausar Edição pela IA")
        self.pause_ia_editor_action.setCheckable(True)
        # TODO: self.pause_ia_editor_action.toggled.connect(self._toggle_ia_editor_pause)

        self.pause_ia_files_action = ia_control_menu.addAction("Pausar Navegação pela IA")
        self.pause_ia_files_action.setCheckable(True)
        # TODO: self.pause_ia_files_action.toggled.connect(self._toggle_ia_files_pause)

        self.pause_ia_terminal_action = ia_control_menu.addAction("Pausar Terminal da IA")
        self.pause_ia_terminal_action.setCheckable(True)
        # TODO: self.pause_ia_terminal_action.toggled.connect(self._toggle_ia_terminal_pause)

        ia_control_menu.addSeparator()

        self.pause_ia_all_action = ia_control_menu.addAction("Pausar Tudo (IA)")
        self.pause_ia_all_action.setCheckable(True)
        # TODO: self.pause_ia_all_action.toggled.connect(self._toggle_ia_all_pause)
        
        # Menu Ajuda (existente)
        help_menu = menu_bar.addMenu("&Ajuda")
        # ... (ações existentes do menu Ajuda) ...
        help_menu.addAction("Sobre")

    def _create_main_layout(self):
        # --- Splitter Principal (Horizontal) ---
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(10)
        main_splitter.setStyleSheet("QSplitter::handle { background-color: lightgray; }")

        # --- NOVO: Painel Esquerdo Combinado (Navegador e Chat) ---
        left_combined_panel_splitter = QSplitter(Qt.Orientation.Vertical)
        left_combined_panel_splitter.setHandleWidth(10) # Alça para o splitter vertical esquerdo
        left_combined_panel_splitter.setStyleSheet("QSplitter::handle { background-color: lightgray; }")


        # --- Sub-Painel Esquerdo Superior (Navegador de Arquivos) ---
        self.file_system_model = QFileSystemModel()
        root_path = QDir.currentPath()
        self.file_system_model.setRootPath(root_path)

        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_system_model)
        self.file_tree.setRootIndex(self.file_system_model.index(root_path))
        self.file_tree.hideColumn(1)
        self.file_tree.hideColumn(2)
        self.file_tree.hideColumn(3)
        self.file_tree.header().setStretchLastSection(False)
        self.file_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_tree.activated.connect(self._open_file_from_tree)
        
        # Adicionar o navegador de arquivos ao splitter vertical esquerdo
        left_combined_panel_splitter.addWidget(self.file_tree)


        # --- Sub-Painel Esquerdo Inferior (Chat com IA) ---
        chat_panel_widget = QWidget()
        chat_layout = QVBoxLayout(chat_panel_widget) # Aplicar layout ao widget
        chat_layout.setContentsMargins(0, 5, 0, 0) # Margens pequenas
        chat_layout.setSpacing(5)

        # ComboBox para seleção de modelo de IA
        self.ai_model_selector = QComboBox()
        self.ai_model_selector.addItem("DeepSeek Coder (Padrão)")
        self.ai_model_selector.addItem("Gemini Pro (Futuro)")
        # TODO: Adicionar lógica para quando o modelo for alterado
        chat_layout.addWidget(self.ai_model_selector)

        # Área de exibição do Chat
        self.chat_display_area = QPlainTextEdit()
        self.chat_display_area.setReadOnly(True)
        self.chat_display_area.setPlaceholderText("Converse com a Aura IA aqui...")
        chat_layout.addWidget(self.chat_display_area, stretch=1) # stretch=1 para ocupar mais espaço

        # --- Área de entrada do Chat (multilinhas com Ctrl+Enter para enviar) ---
        self.chat_input_area_entry = QPlainTextEdit() # Renomeado para evitar conflito com chat_display_area
        self.chat_input_area_entry.setPlaceholderText("Digite sua mensagem... (Ctrl+Enter para enviar)")
        # Definir uma altura máxima/mínima para não ocupar espaço demais inicialmente ou ficar muito pequeno
        self.chat_input_area_entry.setFixedHeight(80) # Altura inicial, pode crescer se necessário
        self.chat_input_widget = ChatInputTextEdit()
        self.chat_input_widget.setPlaceholderText("Digite sua mensagem... (Ctrl+Enter para enviar)")
        self.chat_input_widget.setFixedHeight(80)
        self.chat_input_widget.message_submitted.connect(self._send_chat_message_from_input_widget) # Novo slot

        chat_layout.addWidget(self.chat_input_widget)
        # Adicionar o painel de chat ao splitter vertical esquerdo
        left_combined_panel_splitter.addWidget(chat_panel_widget)

        # Definir tamanhos iniciais para o splitter vertical esquerdo
        # [navegador_arquivos, chat_ia] - Ex: 70% para navegador, 30% para chat
        left_combined_panel_splitter.setSizes([500, 200])


        # Adicionar o splitter vertical esquerdo (combinado) ao splitter principal horizontal
        main_splitter.addWidget(left_combined_panel_splitter)

        # --- Painel Direito (Editor e Terminais - sem alterações aqui por enquanto) ---
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setHandleWidth(10)
        right_splitter.setStyleSheet("QSplitter::handle { background-color: lightgray; }")

        self.editor_area = QPlainTextEdit()
        self.editor_area.setPlaceholderText("Dê um duplo clique em um arquivo para abrí-lo...")
        right_splitter.addWidget(self.editor_area)

        self.user_terminal = SimpleTerminal()
        right_splitter.addWidget(self.user_terminal)

        # --- Terminal 2 (IA) ---
        self.ai_terminal = AITerminalWidget()
        right_splitter.addWidget(self.ai_terminal)

        if hasattr(self, 'ai_terminal') and self.ai_terminal: # Checar se existe
            self.ai_terminal.command_output_ready.connect(self._handle_ai_terminal_output)
            self.ai_terminal.ready_for_next_ai_command.connect(self._ai_terminal_ready_for_command)

        main_splitter.addWidget(right_splitter)

        # Ajustar proporções iniciais dos splitters
        # main_splitter: [painel_esquerdo_combinado, painel_direito]
        main_splitter.setSizes([300, 700]) # Ajuste estes valores conforme necessário
        # right_splitter: [editor, terminal_usuario, terminal_ia]
        right_splitter.setSizes([450, 150, 150])

        self.setCentralWidget(main_splitter)

    def _open_file_from_tree(self, index):
        file_path = self.file_system_model.filePath(index)
        if self.file_system_model.isDir(index):
            if self.file_tree.isExpanded(index):
                self.file_tree.collapse(index)
            else:
                self.file_tree.expand(index)
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            self.editor_area.setPlainText(file_content)
            self.setWindowTitle(f"Aura IDE - {file_path}")
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    file_content = f.read()
                self.editor_area.setPlainText(file_content)
                self.setWindowTitle(f"Aura IDE - {file_path} (latin-1)")
            except Exception as e:
                self.editor_area.setPlainText(f"Não foi possível abrir o arquivo (encoding):\n{file_path}\n\nErro: {e}")
                self.setWindowTitle(f"Aura IDE - Erro ao abrir arquivo")
        except Exception as e:
            self.editor_area.setPlainText(f"Não foi possível abrir o arquivo:\n{file_path}\n\nErro: {e}")
            self.setWindowTitle(f"Aura IDE - Erro ao abrir arquivo")

    def _send_chat_message_from_input_widget(self, message: str):
        if not message.strip():
            return

        self.chat_display_area.appendPlainText(f"Você: {message}")
        QApplication.processEvents()

        if self.ai_provider:
            selected_model_from_combo = self.ai_model_selector.currentText()
            
            if not hasattr(self, 'chat_history_for_ia'):
                self.chat_history_for_ia = []

            if not self.chat_history_for_ia or self.chat_history_for_ia[0].get("role") != "system":
                self.chat_history_for_ia = [msg for msg in self.chat_history_for_ia if msg.get("role") != "system"]
                self.chat_history_for_ia.insert(0, {"role": "system", "content": "Você é Aura, uma assistente de IA. Se você precisar executar um comando no terminal Linux para obter informações ou realizar uma ação, responda APENAS com o prefixo 'EXECUTE_TERMINAL_IA:' seguido do comando. Exemplo: 'EXECUTE_TERMINAL_IA: ls -l'. Para outras respostas, responda normalmente."})
            
            self.chat_history_for_ia.append({"role": "user", "content": message})

            try:
                ai_response_text = self.ai_provider.get_chat_completion(
                    self.chat_history_for_ia, 
                    model_name=selected_model_from_combo
                )
                
                # --- INÍCIO DA LÓGICA PARA EXECUTAR COMANDO DO TERMINAL DA IA ---
                command_prefix = "EXECUTE_TERMINAL_IA:"
                if ai_response_text.strip().startswith(command_prefix):
                    command_to_execute = ai_response_text.strip()[len(command_prefix):].strip()
                    self.chat_display_area.appendPlainText(f"Aura IA (para Terminal): {command_to_execute}")
                    QApplication.processEvents()
                    if hasattr(self, 'ai_terminal') and self.ai_terminal:
                        self.ai_terminal.execute_ai_command(command_to_execute)
                        # A resposta da IA (o próprio comando) não é adicionada ao histórico de chat como 'assistant'
                        # pois a "resposta" real virá da saída do terminal.
                        # Mas podemos remover a última mensagem do usuário do histórico se quisermos
                        # que o feedback do terminal seja o próximo input para a IA.
                        # Por agora, vamos deixar o histórico como está.
                    else:
                        self.chat_display_area.appendPlainText("Aura IA: (Terminal da IA não está disponível para executar o comando)")
                        self.chat_history_for_ia.append({"role": "assistant", "content": "Eu tentei executar um comando, mas meu terminal não está disponível."})
                else:
                    # Resposta normal da IA, exibir no chat e adicionar ao histórico
                    self.chat_display_area.appendPlainText(f"Aura IA: {ai_response_text}")
                    self.chat_history_for_ia.append({"role": "assistant", "content": ai_response_text})
                # --- FIM DA LÓGICA PARA EXECUTAR COMANDO DO TERMINAL DA IA ---

            except Exception as e:
                error_msg = f"Aura IA: (Erro ao obter resposta: {e})"
                self.chat_display_area.appendPlainText(error_msg)
                print(f"Erro na chamada get_chat_completion (Gemini): {e}")
                if self.chat_history_for_ia and self.chat_history_for_ia[-1]['role'] == 'user':
                    self.chat_history_for_ia.pop() # Remove a última pergunta do usuário se a IA falhou
                self.chat_history_for_ia.append({"role": "assistant", "content": error_msg}) # Adiciona erro ao histórico
        else:
            self.chat_display_area.appendPlainText("Aura IA: (Funcionalidade de IA não está configurada ou disponível)")

    def _load_config_and_init_ai(self):
        config = configparser.ConfigParser()
        config_path = QDir.currentPath() + "/config.ini"
        
        ai_successfully_initialized = False

        if not config.read(config_path):
            print(f"AVISO: Arquivo de configuração '{config_path}' não encontrado ou vazio.")
            self._update_ai_status_ui(available=False, message="IA Indisponível - config.ini não encontrado")
            return

        # Tentar Gemini se DeepSeek não foi inicializado com sucesso
        if not ai_successfully_initialized:
            gemini_api_key = config.get('API_KEYS', 'GEMINI_API_KEY', fallback=None)
            if gemini_api_key and gemini_api_key != "SUA_CHAVE_API_GEMINI_AQUI": # Adicione um placeholder se quiser
                try:
                    self.ai_provider = GeminiProvider(api_key=gemini_api_key)
                    print("Provedor Gemini IA inicializado.")
                    self._update_ai_status_ui(available=True, models=self.ai_provider.get_available_models(), provider_name="Gemini")
                    ai_successfully_initialized = True
                except ValueError as ve: # Erros de configuração do GeminiProvider são ValueError
                    print(f"Erro ao inicializar GeminiProvider: {ve}")
                    self.ai_provider = None # Garantir que está None
                    self._update_ai_status_ui(available=False, message=f"Erro Config. Gemini: {str(ve)[:50]}...") # Mensagem curta
            else:
                print("AVISO: GEMINI_API_KEY não encontrada ou não configurada em config.ini.")
        
        if not ai_successfully_initialized:
            # Se nenhum provedor foi inicializado com sucesso
            self.ai_provider = None
            self._update_ai_status_ui(available=False, message="IA Indisponível - Nenhuma chave de API válida")
            if self.chat_display_area: # Verificar se já foi criado
                self.chat_display_area.appendPlainText(
                    "Aura IA: Nenhuma chave de API válida encontrada para DeepSeek ou Gemini. "
                    "Funcionalidades de IA estarão desabilitadas."
                )

    def _update_ai_status_ui(self, available: bool, models: list = None, message: str = None, provider_name: str = ""):
        """Método auxiliar para atualizar a UI relacionada ao status da IA."""
        if self.ai_model_selector: # Checar se o widget existe
            self.ai_model_selector.clear()
            if available and models:
                self.ai_model_selector.addItems(models)
                self.ai_model_selector.setEnabled(True)

                # --- INÍCIO DA MODIFICAÇÃO PARA SELECIONAR O PADRÃO ---
                default_model_to_select = None
                if self.ai_provider and hasattr(self.ai_provider, 'get_default_model_name'):
                    default_model_to_select = self.ai_provider.get_default_model_name()
                
                if default_model_to_select:
                    try:
                        # models é a lista de strings que foi adicionada ao ComboBox
                        index = models.index(default_model_to_select)
                        self.ai_model_selector.setCurrentIndex(index)
                        print(f"Modelo padrão '{default_model_to_select}' selecionado no ComboBox.")
                    except ValueError:
                        # O modelo padrão não está na lista de modelos disponíveis (pode acontecer)
                        print(f"AVISO: Modelo padrão '{default_model_to_select}' não encontrado na lista de modelos disponíveis: {models}")
                        # O ComboBox selecionará o primeiro item por padrão (índice 0) se houver algum.
                # --- FIM DA MODIFICAÇÃO ---
                
                if self.chat_display_area:
                    self.chat_display_area.appendPlainText(f"Aura IA: Conectada ao {provider_name}!")
            else:
                self.ai_model_selector.addItem(message if message else "IA Indisponível")
                self.ai_model_selector.setEnabled(False)

    def _handle_ai_terminal_output(self, command_executed: str, output: str):
        # Este método é chamado quando um comando executado pelo AITerminalWidget termina.
        # A saída já foi mostrada no AITerminalWidget.
        # Agora, podemos informar a IA (via chat) sobre o resultado.
        
        # Limitar o tamanho da saída para não sobrecarregar o chat ou o próximo prompt da IA
        max_output_len = 500 
        truncated_output = output
        if len(output) > max_output_len:
            truncated_output = output[:max_output_len] + "\n... (saída truncada)"

        feedback_to_ia = f"Comando '{command_executed}' executado no meu terminal. Saída:\n{truncated_output}"
        
        self.chat_display_area.appendPlainText(f"Aura IA (Feedback do Terminal): {feedback_to_ia}")
        QApplication.processEvents()

        # Opcional: Enviar este feedback de volta para a IA como uma nova mensagem de "usuário" (ou sistema)
        # para que ela possa continuar a conversa baseada na saída do terminal.
        # Por agora, apenas exibimos no chat.
        #
        # Se quisermos que a IA reaja à saída, faríamos algo como:
        # self.chat_history_for_ia.append({"role": "user", "content": feedback_to_ia}) # Ou role: system
        # # E então, talvez, pedir à IA para analisar ou prosseguir:
        # # self._request_ia_chat_completion("Analise a saída do comando anterior e me diga o que fazer a seguir.")
        #
        # Por enquanto, vamos manter simples e apenas logar.
        print(f"Comando da IA '{command_executed}' finalizado. Saída capturada.")

    def _ai_terminal_ready_for_command(self):
        # Este sinal indica que o terminal da IA está pronto para um novo comando.
        # Podemos usar isso para gerenciar um fluxo de comandos da IA, se necessário.
        # Por agora, apenas um log.
        print("Terminal da IA está pronto para o próximo comando.")
        # Poderíamos ter uma fila de comandos da IA aqui, ou um estado que indica
        # se a IA está esperando para executar um comando.