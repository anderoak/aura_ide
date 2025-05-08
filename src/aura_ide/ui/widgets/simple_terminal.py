from PySide6.QtWidgets import QPlainTextEdit, QApplication
from PySide6.QtCore import QProcess, Qt, QTimer
from PySide6.QtGui import QFont, QTextCursor, QColor, QKeySequence

class SimpleTerminal(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.prompt_str = "$ "
        self.current_path_str = "~"
        self.history = []
        self.history_index = -1
        self.current_command_start_pos = 0
        self.unique_end_marker = "###AURA_IDE_CMD_END###"
        self.is_processing_initial_prompt = True

        self._setup_ui()
        self._start_shell_process()
        self._send_initial_commands()

    def _setup_ui(self):
        font = QFont("Monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(10)
        self.setFont(font)
        self.setStyleSheet("QPlainTextEdit { background-color: #282c34; color: #abb2bf; border: none; }")
        self.setUndoRedoEnabled(False)

    def _start_shell_process(self):
        self.process.readyReadStandardOutput.connect(self._handle_shell_output)
        self.process.finished.connect(self._handle_shell_finished)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        shell_program = "/bin/bash"
        self.process.start(shell_program)

        if not self.process.waitForStarted(1000):
            self._append_output_text(f"Erro: Não foi possível iniciar o shell '{shell_program}'.\n", is_error=True)
            self.is_processing_initial_prompt = False
            self._display_prompt() # Exibir prompt mesmo com erro para permitir interação mínima

    def _send_initial_commands(self):
        if self.process.state() == QProcess.ProcessState.Running:
            self.is_processing_initial_prompt = True
            self.process.write(f"pwd; echo '{self.unique_end_marker}'\n".encode())
        else:
            self.is_processing_initial_prompt = False
            self._display_prompt()

    def _get_full_prompt(self):
        return f"{self.current_path_str}{self.prompt_str}"

    def _display_prompt(self):
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertPlainText(self._get_full_prompt())
        self.current_command_start_pos = self.textCursor().position()
        self.ensureCursorVisible()

    def _append_output_text(self, text, is_error=False):
        self.moveCursor(QTextCursor.MoveOperation.End)
        original_format = self.currentCharFormat()
        if is_error:
            error_format = self.currentCharFormat()
            error_format.setForeground(QColor("red"))
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
            text_before_marker = parts[0]

            if self.is_processing_initial_prompt:
                lines = text_before_marker.strip().split('\n')
                if lines:
                    self.current_path_str = lines[0].strip()
                self.is_processing_initial_prompt = False
            else:
                # Processar saída do comando e PWD
                # Remover o último PWD da saída visível se for o caso
                lines = text_before_marker.strip().split('\n')
                if len(lines) > 1 : # Múltiplas linhas de saída + PWD
                    self.current_path_str = lines[-1].strip() # Última linha é o PWD
                    self._append_output_text("\n".join(lines[:-1]) + "\n") # Saída do comando
                elif lines: # Apenas uma linha (pode ser só o PWD ou saída curta)
                    # Se a saída não for o PWD (ex: 'cd' não produz saída mas atualiza PWD)
                    # ou se for um comando que produz uma única linha de saída
                    potential_pwd = lines[0].strip()
                    if potential_pwd.startswith("/") or potential_pwd == "~" : # Heurística simples para PWD
                        self.current_path_str = potential_pwd
                        # Não exibir o PWD se for a única coisa e o comando não deveria ter produzido saída visível
                        # Este 'if' pode precisar de refinamento.
                        # Por agora, vamos exibir para depuração, mas pode ser que o 'pwd' extra seja desnecessário visualmente.
                        # self._append_output_text(potential_pwd + "\n") # Descomente para ver o PWD extra
                    else: # Saída de comando de uma linha
                        self._append_output_text(lines[0] + "\n")


            self._display_prompt()

            if len(parts) > 1 and parts[1].strip():
                self._append_output_text(parts[1])
        else:
            self._append_output_text(output_text)

    def _process_command_input(self, command_str):
        if not command_str.strip(): # Comando vazio
            self._append_output_text("\n") # Nova linha para o próximo prompt
            self._display_prompt()
            return

        if not self.history or self.history[-1] != command_str: # Evitar duplicados consecutivos no histórico
            self.history.append(command_str)
        self.history_index = len(self.history) # Aponta para depois do último item para novo comando
        self._append_output_text("\n")

        # Enviar comando para o shell, seguido por 'pwd' e o marcador
        full_shell_command = f"{command_str.strip()}; pwd; echo '{self.unique_end_marker}'\n"
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.write(full_shell_command.encode())
        else:
            self._append_output_text("Erro: Shell não está rodando.\n", is_error=True)
            self._display_prompt()

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        is_editable_area = cursor.position() >= self.current_command_start_pos

        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if is_editable_area: # Só processar se estiver na área de comando
                command_text = self.toPlainText()[self.current_command_start_pos:]
                self.moveCursor(QTextCursor.MoveOperation.End)
                self._process_command_input(command_text.strip())
            else: # Se o Enter for pressionado na área de saída, mover para o fim
                self.moveCursor(QTextCursor.MoveOperation.End)
            return

        # Permitir navegação e cópia sempre
        if event.matches(QKeySequence.StandardKey.Copy) or \
           event.key() in (Qt.Key.Key_PageUp, Qt.Key.Key_PageDown,
                           Qt.Key.Key_Home, Qt.Key.Key_End):
            super().keyPressEvent(event) # Deixar o QPlainTextEdit lidar com isso
            return

        # Setas para cima/baixo (histórico) e esquerda/direita (navegação no comando)
        # só devem funcionar na área editável ou ter comportamento especial
        if is_editable_area:
            if event.key() == Qt.Key.Key_Up:
                if self.history_index > 0:
                    self.history_index -= 1
                    self._replace_current_command_text(self.history[self.history_index])
                elif self.history and self.history_index == 0: # Já no primeiro item
                    self._replace_current_command_text(self.history[0])
                return
            elif event.key() == Qt.Key.Key_Down:
                if self.history_index < len(self.history) -1:
                    self.history_index += 1
                    self._replace_current_command_text(self.history[self.history_index])
                else: # No fim do histórico ou além
                    self.history_index = len(self.history) # Preparar para novo comando
                    self._replace_current_command_text("")
                return
            # Permitir outras teclas (incluindo Backspace, Delete, Left, Right) na área editável
            super().keyPressEvent(event)
        else: # Não está na área editável
            # Permitir setas para cima/baixo para scrollar a saída
            if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                super().keyPressEvent(event)
            # Bloquear outras teclas de edição na área de saída
            return

    def _replace_current_command_text(self, text):
        cursor = self.textCursor()
        cursor.beginEditBlock() # Agrupar operações de undo, embora undo esteja desabilitado
        cursor.setPosition(self.current_command_start_pos)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(text)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def _handle_shell_finished(self, exitCode, exitStatus):
        self._append_output_text(f"\nProcesso do shell terminado (Código: {exitCode}, Status: {exitStatus}).\n", is_error=True)

    def closeEvent(self, event):
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.process.waitForFinished(1000)
        super().closeEvent(event)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    terminal_widget = SimpleTerminal()
    terminal_widget.resize(700, 500)
    terminal_widget.show()
    sys.exit(app.exec())