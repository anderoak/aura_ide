from PySide6.QtWidgets import QPlainTextEdit, QApplication
from PySide6.QtCore import QProcess, Qt, Signal
from PySide6.QtGui import QFont, QTextCursor, QColor

class AITerminalWidget(QPlainTextEdit):
    # Sinal emitido quando um comando termina de executar e sua saída (parcial ou total) está disponível
    # Poderia emitir (str: command, str: output, int: exit_code)
    command_output_ready = Signal(str, str) # (comando_original, saida_completa_do_comando)
    # Sinal para quando o prompt estiver pronto para um novo comando da IA
    ready_for_next_ai_command = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.prompt_str = "# IA $ " # Prompt diferente para o terminal da IA
        self.current_path_str = "~"
        self.unique_end_marker = "###AURA_IDE_AI_CMD_END###"
        self.is_processing_initial_prompt = True
        self.current_ai_command = None # Para rastrear o comando que a IA enviou

        self._setup_ui()
        self._start_shell_process()
        self._send_initial_commands()

    def _setup_ui(self):
        font = QFont("Monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(10)
        self.setFont(font)
        # Tema um pouco diferente para distinguir visualmente (opcional)
        self.setStyleSheet("QPlainTextEdit { background-color: #2E3440; color: #D8DEE9; border: none; }") # Nord theme-ish
        self.setReadOnly(True) # Este terminal é apenas para saída e comandos programáticos
        self.setUndoRedoEnabled(False)

    def _start_shell_process(self):
        self.process.readyReadStandardOutput.connect(self._handle_shell_output)
        self.process.finished.connect(self._handle_shell_finished)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        # TODO: Considerar rodar com um usuário de privilégios mínimos específico para a IA
        shell_program = "/bin/bash" 
        self.process.start(shell_program)

        if not self.process.waitForStarted(1000):
            self._append_output_text(f"Erro: Não foi possível iniciar o shell da IA '{shell_program}'.\n", is_error=True)
            self.is_processing_initial_prompt = False
            self.ready_for_next_ai_command.emit() # Mesmo com erro, sinalizar que pode tentar (ou falhar)

    def _send_initial_commands(self):
        if self.process.state() == QProcess.ProcessState.Running:
            self.is_processing_initial_prompt = True
            self.process.write(f"pwd; echo '{self.unique_end_marker}'\n".encode())
        else:
            self.is_processing_initial_prompt = False
            self._display_prompt(initial=True) # Exibe o prompt inicial
            self.ready_for_next_ai_command.emit()


    def _get_full_prompt(self):
        return f"{self.current_path_str}{self.prompt_str}"

    def _display_prompt(self, initial=False):
        self.moveCursor(QTextCursor.MoveOperation.End)
        if not initial: # Não adicionar nova linha antes do primeiro prompt
             self.insertPlainText("\n")
        self.insertPlainText(self._get_full_prompt())
        self.ensureCursorVisible()

    def _append_output_text(self, text, is_error=False):
        self.moveCursor(QTextCursor.MoveOperation.End)
        original_format = self.currentCharFormat()
        if is_error:
            error_format = self.currentCharFormat()
            error_format.setForeground(QColor("orange")) # Erros da IA em laranja/amarelo
            self.setCurrentCharFormat(error_format)

        self.insertPlainText(text)

        if is_error:
            self.setCurrentCharFormat(original_format)
        self.ensureCursorVisible()

    def _handle_shell_output(self):
        raw_data = self.process.readAllStandardOutput()
        output_text = raw_data.data().decode(errors='replace')

        if self.unique_end_marker in output_text:
            parts = output_text.split(self.unique_end_marker, 1)
            text_before_marker = parts[0].strip() # Saída do comando + pwd

            # A saída do comando é tudo antes do último PWD
            lines = text_before_marker.split('\n')
            command_actual_output = ""
            
            if self.is_processing_initial_prompt:
                if lines: self.current_path_str = lines[0] # PWD é a primeira linha
                # Não há "saída de comando" real para o PWD inicial
                self.is_processing_initial_prompt = False
            else:
                if len(lines) > 1:
                    self.current_path_str = lines[-1] # Última linha é o novo PWD
                    command_actual_output = "\n".join(lines[:-1]) # Tudo menos o último PWD
                elif lines: # Apenas uma linha (pode ser só PWD ou saída curta)
                    # Se a única linha for o PWD, a saída do comando é vazia
                    if lines[0].startswith("/") or lines[0] == "~": # Heurística para PWD
                        self.current_path_str = lines[0]
                    else: # Saída de comando de uma linha, PWD não mudou (ou não foi pego)
                        command_actual_output = lines[0]
                
                # Emitir o sinal com a saída do comando
                if self.current_ai_command:
                    self._append_output_text(f"{command_actual_output}\n" if command_actual_output else "\n")
                    self.command_output_ready.emit(self.current_ai_command, command_actual_output)
                    self.current_ai_command = None # Resetar para o próximo comando

            self._display_prompt() # Mostrar novo prompt da IA
            self.ready_for_next_ai_command.emit() # IA está pronta para o próximo comando

            if len(parts) > 1 and parts[1].strip(): # Texto residual após marcador
                self._append_output_text(parts[1])
        else:
            # Saída intermediária, apenas anexa (não emite sinal ainda)
            self._append_output_text(output_text)
            
    def execute_ai_command(self, command_str: str):
        if not command_str.strip():
            self.ready_for_next_ai_command.emit() # Se comando vazio, está pronto
            return

        if self.process.state() != QProcess.ProcessState.Running:
            error_msg = "Erro: Shell da IA não está rodando."
            self._append_output_text(f"{self._get_full_prompt()}{command_str}\n{error_msg}\n", is_error=True)
            self.command_output_ready.emit(command_str, error_msg)
            self._display_prompt()
            self.ready_for_next_ai_command.emit()
            return

        self.current_ai_command = command_str.strip()
        # Mostrar o comando que a IA está executando
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertPlainText(f"{self.current_ai_command}\n") # Ecoar o comando da IA
        self.ensureCursorVisible()
        QApplication.processEvents() # Atualizar UI

        full_shell_command = f"{self.current_ai_command}; pwd; echo '{self.unique_end_marker}'\n"
        self.process.write(full_shell_command.encode())


    def _handle_shell_finished(self, exitCode, exitStatus):
        msg = f"\nProcesso do shell da IA terminado (Código: {exitCode}, Status: {exitStatus}).\n"
        self._append_output_text(msg, is_error=True)
        self.ready_for_next_ai_command.emit() # Pode não ser ideal, mas sinaliza o fim

    def closeEvent(self, event):
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.process.waitForFinished(1000)
        super().closeEvent(event)

# Bloco para teste isolado (opcional)
if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    ai_terminal = AITerminalWidget()
    ai_terminal.resize(700, 300)
    ai_terminal.show()

    def run_test_commands():
        print("Teste: Enviando 'ls -l'")
        ai_terminal.execute_ai_command("ls -l")

    def handle_output(cmd, output):
        print(f"Saída do comando '{cmd}':\n---\n{output}\n---")
        if cmd == "ls -l":
            print("Teste: Enviando 'echo \"Olá do Terminal da IA\"'")
            ai_terminal.execute_ai_command("echo \"Olá do Terminal da IA\"")
        elif cmd.startswith("echo"):
            print("Teste: Fim dos comandos de teste.")
            # app.quit()

    def ready_for_next():
        print("Terminal da IA pronto para o próximo comando.")

    ai_terminal.command_output_ready.connect(handle_output)
    ai_terminal.ready_for_next_ai_command.connect(ready_for_next)
    
    # --- INÍCIO DA CORREÇÃO ---
    # Usar uma lista para encapsular o estado do flag
    initial_prompt_processed_container = [False] 

    def on_first_ready():
        # Acessar e modificar o conteúdo da lista
        if not initial_prompt_processed_container[0]:
            initial_prompt_processed_container[0] = True
            print("Primeiro 'ready_for_next_ai_command' recebido, executando comandos de teste.")
            run_test_commands()
            # Desconectar para não chamar run_test_commands múltiplas vezes
            try:
                ai_terminal.ready_for_next_ai_command.disconnect(on_first_ready)
            except RuntimeError:
                pass
    # --- FIM DA CORREÇÃO ---

    ai_terminal.ready_for_next_ai_command.connect(on_first_ready)

    sys.exit(app.exec())