from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent

class ChatInputTextEdit(QPlainTextEdit):
    # Sinal que será emitido com o texto quando Ctrl+Enter for pressionado
    message_submitted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event: QKeyEvent):
        # Verificar se Ctrl (ou Command no Mac) + Enter foi pressionado
        is_ctrl_pressed = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        is_command_pressed = event.modifiers() & Qt.KeyboardModifier.MetaModifier # Para macOS Command key
        
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and \
           (is_ctrl_pressed or is_command_pressed):
            
            text_content = self.toPlainText().strip()
            if text_content:
                self.message_submitted.emit(text_content) # Emitir o sinal com o texto
                self.clear() # Limpar o campo de entrada após enviar
            event.accept() # Consumir o evento para não inserir nova linha
        else:
            # Para qualquer outra tecla (incluindo Enter sozinho), usar o comportamento padrão
            super().keyPressEvent(event)