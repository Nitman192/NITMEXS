"""PyQt6 main window for minimal student exam flow."""

from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiError, NITMEXSApiClient


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NITMEXS Desktop Client")
        self.resize(700, 500)

        self.api_client = NITMEXSApiClient("http://127.0.0.1:8000")
        self.student_id = ""
        self.attempt_id = ""
        self.current_sequence = 1
        self.current_question: dict[str, Any] | None = None

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_page = self._build_login_page()
        self.exams_page = self._build_exams_page()
        self.exam_page = self._build_exam_page()
        self.result_page = self._build_result_page()

        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.exams_page)
        self.stack.addWidget(self.exam_page)
        self.stack.addWidget(self.result_page)

    def _build_login_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        form = QFormLayout()
        self.server_url_input = QLineEdit("http://127.0.0.1:8000")
        self.student_id_input = QLineEdit()
        form.addRow("Server URL", self.server_url_input)
        form.addRow("Student ID", self.student_id_input)

        login_button = QPushButton("Login")
        login_button.clicked.connect(self.login)

        layout.addLayout(form)
        layout.addWidget(login_button)
        layout.addStretch()
        return page

    def _build_exams_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.exam_list = QListWidget()
        refresh_button = QPushButton("Refresh Published Exams")
        refresh_button.clicked.connect(self.load_exams)

        start_button = QPushButton("Start Selected Exam")
        start_button.clicked.connect(self.start_selected_exam)

        layout.addWidget(QLabel("Published Exams"))
        layout.addWidget(self.exam_list)
        layout.addWidget(refresh_button)
        layout.addWidget(start_button)
        return page

    def _build_exam_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.question_label = QLabel("Question")
        self.question_label.setWordWrap(True)

        self.option_group = QButtonGroup(self)
        self.option_buttons: list[QRadioButton] = []
        for _ in range(4):
            button = QRadioButton()
            self.option_group.addButton(button)
            self.option_buttons.append(button)
            layout.addWidget(button)

        buttons_layout = QHBoxLayout()
        submit_button = QPushButton("Submit Answer")
        submit_button.clicked.connect(self.submit_answer)
        next_button = QPushButton("Next Question")
        next_button.clicked.connect(self.next_question)
        finalize_button = QPushButton("Finalize Exam")
        finalize_button.clicked.connect(self.finalize_exam)

        buttons_layout.addWidget(submit_button)
        buttons_layout.addWidget(next_button)
        buttons_layout.addWidget(finalize_button)

        layout.insertWidget(0, self.question_label)
        layout.addLayout(buttons_layout)
        return page

    def _build_result_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.result_label = QLabel("Result summary")
        self.result_label.setWordWrap(True)

        restart_button = QPushButton("Back to Exams")
        restart_button.clicked.connect(self.back_to_exams)

        layout.addWidget(self.result_label)
        layout.addWidget(restart_button)
        return page

    def login(self) -> None:
        server_url = self.server_url_input.text().strip()
        student_id = self.student_id_input.text().strip()
        if not server_url or not student_id:
            self._show_error("Server URL and Student ID are required.")
            return

        self.api_client = NITMEXSApiClient(server_url)
        self.student_id = student_id
        self.load_exams()
        self.stack.setCurrentWidget(self.exams_page)

    def load_exams(self) -> None:
        try:
            exams = self.api_client.list_published_exams()
        except ApiError as exc:
            self._handle_api_error(exc)
            return

        self.exam_list.clear()
        for exam in exams:
            item = QListWidgetItem(f"{exam.name} ({exam.duration_minutes} min)")
            item.setData(1, exam.exam_id)
            self.exam_list.addItem(item)

    def start_selected_exam(self) -> None:
        current_item = self.exam_list.currentItem()
        if current_item is None:
            self._show_error("Select an exam first.")
            return

        exam_id = current_item.data(1)
        try:
            data = self.api_client.start_exam(self.student_id, exam_id)
        except ApiError as exc:
            self._handle_api_error(exc)
            return

        self.attempt_id = data["attempt_id"]
        first_question = data["first_question"]
        self.current_sequence = int(first_question["sequence_number"])
        self._render_question(first_question)
        self.stack.setCurrentWidget(self.exam_page)

    def submit_answer(self) -> None:
        if not self.current_question:
            return

        selected = self.option_group.checkedButton()
        if selected is None:
            self._show_error("Select an option before submitting.")
            return

        selected_option_id = selected.property("option_id")
        question_id = self.current_question["question"]["id"]

        try:
            self.api_client.submit_answer(
                self.student_id,
                self.attempt_id,
                question_id,
                selected_option_id,
            )
            QMessageBox.information(self, "Submitted", "Answer submitted.")
        except ApiError as exc:
            self._handle_api_error(exc)

    def next_question(self) -> None:
        next_sequence = self.current_sequence + 1
        try:
            question = self.api_client.fetch_question(
                self.student_id,
                self.attempt_id,
                next_sequence,
            )
        except ApiError as exc:
            if exc.status_code == 404:
                QMessageBox.information(self, "End", "No more questions. Please finalize.")
                return
            self._handle_api_error(exc)
            return

        self.current_sequence = next_sequence
        self._render_question(question)

    def finalize_exam(self) -> None:
        try:
            self.api_client.finalize_exam(self.student_id, self.attempt_id)
            result = self.api_client.get_result(self.student_id, self.attempt_id)
        except ApiError as exc:
            self._handle_api_error(exc)
            return

        self.result_label.setText(
            "\n".join(
                [
                    f"Attempt: {result.get('attempt_id', self.attempt_id)}",
                    f"Score: {result.get('total_score', 0)} / {result.get('total_possible_marks', 0)}",
                    f"Percentage: {result.get('percentage', 0):.2f}%",
                    f"Passed: {result.get('passed', False)}",
                ]
            )
        )
        self.stack.setCurrentWidget(self.result_page)

    def back_to_exams(self) -> None:
        self.current_question = None
        self.current_sequence = 1
        self.attempt_id = ""
        self.load_exams()
        self.stack.setCurrentWidget(self.exams_page)

    def _render_question(self, payload: dict[str, Any]) -> None:
        self.current_question = payload
        question = payload["question"]
        self.question_label.setText(f"Q{payload['sequence_number']}: {question['text']}")

        self.option_group.setExclusive(False)
        for button in self.option_buttons:
            button.setChecked(False)
            button.hide()
        self.option_group.setExclusive(True)

        for idx, option in enumerate(payload.get("options", [])):
            if idx >= len(self.option_buttons):
                break
            button = self.option_buttons[idx]
            button.setText(option["option_text"])
            button.setProperty("option_id", option["id"])
            button.show()

    def _handle_api_error(self, exc: ApiError) -> None:
        if exc.status_code == 401:
            self._show_error(f"Unauthorized: {exc.message}")
            self.stack.setCurrentWidget(self.login_page)
            return
        if exc.status_code == 403:
            self._show_error(f"Forbidden: {exc.message}")
            return
        if exc.status_code == 409:
            self._show_error(f"Conflict: {exc.message}")
            return
        self._show_error(f"Error ({exc.status_code}): {exc.message}")

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)
