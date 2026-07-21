APP_STYLE = r"""
* {
    font-family: "Microsoft YaHei UI", "Segoe UI";
    font-size: 13px;
    color: #172033;
}
QMainWindow, QWidget#appRoot, QStackedWidget#contentStack {
    background: #f3f6fb;
}
QFrame#sidebar {
    background: #0d1729;
    border: none;
}
QLabel#brandMark {
    background: #3978f6;
    color: white;
    border-radius: 12px;
    font-family: "Segoe UI Symbol";
    font-size: 25px;
    font-weight: 700;
}
QLabel#brandTitle {
    color: #ffffff;
    font-size: 19px;
    font-weight: 700;
}
QLabel#brandSubtitle {
    color: #7f8da7;
    font-size: 9px;
}
QLabel#navSection {
    color: #63718c;
    font-size: 10px;
    font-weight: 700;
    padding-left: 11px;
}
QPushButton#navButton {
    background: transparent;
    color: #aab5c8;
    border: none;
    border-radius: 9px;
    padding: 11px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#navButton:hover {
    background: #15243b;
    color: #ffffff;
}
QPushButton#navButton:checked {
    background: #1b3151;
    color: #ffffff;
    border-left: 3px solid #4f8cff;
    padding-left: 11px;
}
QFrame#adminCard {
    background: #132239;
    border: 1px solid #20334f;
    border-radius: 11px;
}
QLabel#adminTitle {
    color: #e5ebf5;
    font-weight: 600;
}
QLabel#adminSubtitle {
    color: #7f8da7;
    font-size: 10px;
}
QLabel#adminDot {
    background: #22c784;
    border-radius: 5px;
    min-width: 10px;
    max-width: 10px;
    min-height: 10px;
    max-height: 10px;
}
QWidget#page {
    background: #f3f6fb;
}
QLabel#pageTitle {
    color: #111b2e;
    font-size: 27px;
    font-weight: 700;
}
QLabel#pageSubtitle {
    color: #718096;
    font-size: 12px;
}
QFrame#card, QFrame#tableCard, QFrame#statCard, QFrame#infoBanner {
    background: #ffffff;
    border: 1px solid #e3e9f2;
    border-radius: 13px;
}
QFrame#statCard:hover {
    border: 1px solid #cfdaf0;
}
QLabel#statLabel {
    color: #7b879b;
    font-size: 11px;
    font-weight: 600;
}
QLabel#statValue {
    color: #162139;
    font-size: 28px;
    font-weight: 700;
}
QLabel#statHint {
    color: #98a3b5;
    font-size: 10px;
}
QLabel#statIconBlue, QLabel#statIconGreen, QLabel#statIconPurple, QLabel#statIconOrange {
    border-radius: 11px;
    font-family: "Segoe UI Symbol";
    font-size: 20px;
    font-weight: 700;
    min-width: 43px;
    max-width: 43px;
    min-height: 43px;
    max-height: 43px;
    qproperty-alignment: AlignCenter;
}
QLabel#statIconBlue { background: #eaf1ff; color: #3978f6; }
QLabel#statIconGreen { background: #e7f8f1; color: #18a86f; }
QLabel#statIconPurple { background: #f1ebff; color: #7d55e7; }
QLabel#statIconOrange { background: #fff1df; color: #e38a24; }
QLabel#sectionTitle {
    color: #1c263a;
    font-size: 15px;
    font-weight: 700;
}
QLabel#sectionSubtitle, QLabel#mutedLabel {
    color: #8995a8;
    font-size: 11px;
}
QPushButton#primaryButton, QPushButton#secondaryButton, QPushButton#dangerButton,
QPushButton#ghostButton {
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    min-height: 18px;
}
QPushButton#primaryButton {
    background: #3978f6;
    color: white;
    border: 1px solid #3978f6;
}
QPushButton#primaryButton:hover { background: #2868e7; }
QPushButton#primaryButton:pressed { background: #1f5ccf; }
QPushButton#secondaryButton {
    background: #ffffff;
    color: #344158;
    border: 1px solid #d8e0ec;
}
QPushButton#secondaryButton:hover { background: #f7f9fc; border-color: #c2cddd; }
QPushButton#dangerButton {
    background: #fff4f3;
    color: #d94b44;
    border: 1px solid #ffd9d5;
}
QPushButton#dangerButton:hover { background: #ffe9e7; }
QPushButton#ghostButton {
    background: transparent;
    color: #3978f6;
    border: none;
    padding: 6px 8px;
}
QPushButton:disabled {
    color: #aab3c1;
    background: #edf0f5;
    border-color: #e2e6ed;
}
QLineEdit, QComboBox, QSpinBox {
    background: #ffffff;
    color: #202a3c;
    border: 1px solid #d9e1ec;
    border-radius: 8px;
    padding: 8px 11px;
    min-height: 19px;
    selection-background-color: #3978f6;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #3978f6;
}
QLineEdit#searchInput {
    padding-left: 13px;
    min-width: 240px;
}
QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background: white;
    border: 1px solid #d8e0ec;
    border-radius: 6px;
    selection-background-color: #eaf1ff;
    selection-color: #1c263a;
    padding: 4px;
}
QTableView {
    background: #ffffff;
    alternate-background-color: #fafbfd;
    border: none;
    gridline-color: transparent;
    selection-background-color: #eaf1ff;
    selection-color: #172033;
    outline: none;
}
QTableView::item {
    border-bottom: 1px solid #edf0f5;
    padding: 8px 7px;
}
QTableView::item:selected {
    border-bottom: 1px solid #d8e5ff;
}
QHeaderView::section {
    background: #f8fafc;
    color: #778398;
    border: none;
    border-bottom: 1px solid #e5eaf2;
    padding: 9px 7px;
    font-size: 10px;
    font-weight: 700;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 3px;
}
QScrollBar::handle:vertical {
    background: #ccd4e1;
    border-radius: 3px;
    min-height: 36px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QLabel#statusUp {
    color: #159b68;
    background: #e8f8f1;
    border-radius: 9px;
    padding: 3px 8px;
    font-size: 10px;
    font-weight: 600;
}
QLabel#statusDown {
    color: #7d8798;
    background: #edf0f4;
    border-radius: 9px;
    padding: 3px 8px;
    font-size: 10px;
    font-weight: 600;
}
QProgressBar#busyBar {
    background: transparent;
    border: none;
    max-height: 3px;
    min-height: 3px;
}
QProgressBar#busyBar::chunk { background: #3978f6; border-radius: 1px; }
QLabel#footerStatus {
    color: #7b879b;
    font-size: 11px;
}
QDialog {
    background: #f6f8fc;
}
QFrame#dialogHeader {
    background: #ffffff;
    border: none;
    border-bottom: 1px solid #e5eaf2;
}
QLabel#dialogTitle {
    color: #152039;
    font-size: 21px;
    font-weight: 700;
}
QLabel#dialogSubtitle {
    color: #7b879b;
    font-size: 11px;
}
QLabel#fieldLabel {
    color: #374158;
    font-weight: 600;
    font-size: 11px;
}
QLabel#fieldHint {
    color: #929daf;
    font-size: 10px;
}
QLabel#errorLabel {
    color: #cc423c;
    background: #fff0ef;
    border: 1px solid #ffd8d4;
    border-radius: 7px;
    padding: 8px 10px;
}
QFrame#storeNotice {
    background: #edf4ff;
    border: 1px solid #d6e5ff;
    border-radius: 9px;
}
QLabel#storeNoticeTitle { color: #2868d7; font-weight: 700; }
QLabel#storeNoticeText { color: #587096; font-size: 10px; }
QToolTip {
    background: #17233a;
    color: white;
    border: none;
    padding: 5px 7px;
}
"""
