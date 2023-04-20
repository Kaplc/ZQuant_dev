from typing import List, Tuple, Dict, Optional
from functools import partial
from datetime import datetime, timedelta

from core.trader.ui import QtWidgets, QtCore
from core.trader.engine import MainEngine, EventEngine
from core.trader.constant import Interval, Exchange
from core.trader.object import BarData
from core.trader.database import DB_TZ
from core.trader.utility import available_timezones

from ..engine import APP_NAME, ManagerEngine, BarOverview


class ManagerWidget(QtWidgets.QWidget):
    """"""

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """"""
        super().__init__()

        self.engine: ManagerEngine = main_engine.get_engine(APP_NAME)

        self.tree_items: Dict[tuple, QtWidgets.QTreeWidgetItem] = {}

        self.init_ui()

    def init_ui(self) -> None:
        """界面"""
        self.setWindowTitle("数据管理")

        self.init_tree()
        self.init_table()
        self.init_child()
        self.refresh_tree()  # 进入ui自动刷新

        refresh_button: QtWidgets.QPushButton = QtWidgets.QPushButton("刷新")
        refresh_button.clicked.connect(self.refresh_tree)

        import_button: QtWidgets.QPushButton = QtWidgets.QPushButton("导入数据")
        import_button.clicked.connect(self.import_data)

        update_button: QtWidgets.QPushButton = QtWidgets.QPushButton("更新数据")
        update_button.clicked.connect(self.update_data)

        download_button: QtWidgets.QPushButton = QtWidgets.QPushButton("下载数据")
        download_button.clicked.connect(self.download_data)

        hbox1: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox1.addWidget(refresh_button)
        hbox1.addStretch()
        hbox1.addWidget(import_button)
        hbox1.addWidget(update_button)
        hbox1.addWidget(download_button)

        hbox2: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox2.addWidget(self.tree)
        hbox2.addWidget(self.table)

        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)

        self.setLayout(vbox)

    def init_tree(self) -> None:
        """"""
        labels: list = [
            "数据",
            "本地代码",
            "代码",
            "交易所",
            "数据量",
            "开始时间",
            "结束时间",
            "",
            "",
            ""
        ]

        self.tree: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget()
        self.tree.setColumnCount(len(labels))
        self.tree.setHeaderLabels(labels)

    def init_child(self) -> None:
        """"""
        self.minute_child: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem()
        self.minute_child.setText(0, "分钟线")
        self.tree.addTopLevelItem(self.minute_child)

        self.hour_child: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem(self.tree)
        self.hour_child.setText(0, "小时线")
        self.tree.addTopLevelItem(self.hour_child)

        self.daily_child: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem(self.tree)
        self.daily_child.setText(0, "日线")
        self.tree.addTopLevelItem(self.daily_child)

    def init_table(self) -> None:
        """"""
        labels: list = [
            "时间",
            "开盘价",
            "最高价",
            "最低价",
            "收盘价",
            "成交量",
            "成交额",
            "持仓量"
        ]

        self.table: QtWidgets.QTableWidget = QtWidgets.QTableWidget()
        self.table.setColumnCount(len(labels))
        self.table.setHorizontalHeaderLabels(labels)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )

    def clear_tree(self) -> None:
        """"""
        for key, item in self.tree_items.items():
            interval: str = key[2]

            if interval == Interval.MINUTE:
                self.minute_child.removeChild(item)
            elif interval == Interval.HOUR:
                self.hour_child.removeChild(item)
            else:
                self.daily_child.removeChild(item)

        self.tree_items.clear()

    def refresh_tree(self) -> None:
        """"""
        self.clear_tree()

        overviews: List[BarOverview] = self.engine.get_bar_overview()

        # 基于合约代码进行排序
        overviews.sort(key=lambda x: x.symbol)

        for overview in overviews:
            key: tuple = (overview.symbol, overview.exchange, overview.interval)
            item: Optional[QtWidgets.QTreeWidgetItem] = self.tree_items.get(key, None)

            if not item:
                item = QtWidgets.QTreeWidgetItem()
                self.tree_items[key] = item

                item.setText(1, f"{overview.symbol}.{overview.exchange.value}")
                item.setText(2, overview.symbol)
                item.setText(3, overview.exchange.value)

                if overview.interval == Interval.MINUTE:
                    self.minute_child.addChild(item)
                elif overview.interval == Interval.HOUR:
                    self.hour_child.addChild(item)
                else:
                    self.daily_child.addChild(item)

                output_button: QtWidgets.QPushButton = QtWidgets.QPushButton("导出")
                output_func = partial(
                    self.output_data,
                    overview.symbol,
                    overview.exchange,
                    overview.interval,
                    overview.start,
                    overview.end
                )
                output_button.clicked.connect(output_func)

                show_button: QtWidgets.QPushButton = QtWidgets.QPushButton("查看")
                show_func = partial(
                    self.show_data,
                    overview.symbol,
                    overview.exchange,
                    overview.interval,
                    overview.start,
                    overview.end
                )
                show_button.clicked.connect(show_func)

                delete_button: QtWidgets.QPushButton = QtWidgets.QPushButton("删除")
                delete_func = partial(
                    self.delete_data,
                    overview.symbol,
                    overview.exchange,
                    overview.interval,

                )

                delete_button.clicked.connect(delete_func)

                self.tree.setItemWidget(item, 7, show_button)
                self.tree.setItemWidget(item, 8, output_button)
                self.tree.setItemWidget(item, 9, delete_button)

            item.setText(4, str(overview.count))
            item.setText(5, overview.start.strftime("%Y-%m-%d %H:%M:%S"))
            item.setText(6, overview.end.strftime("%Y-%m-%d %H:%M:%S"))

        self.minute_child.setExpanded(True)
        self.hour_child.setExpanded(True)
        self.daily_child.setExpanded(True)

    def import_data(self) -> None:
        """"""
        dialog: ImportDialog = ImportDialog()
        n: int = dialog.exec_()
        if n != dialog.Accepted:
            return

        file_path: str = dialog.file_edit.text()
        symbol: str = dialog.symbol_edit.text()
        exchange = dialog.exchange_combo.currentData()
        interval = dialog.interval_combo.currentData()
        tz_name: str = dialog.tz_combo.currentText()
        datetime_head: str = dialog.datetime_edit.text()
        open_head: str = dialog.open_edit.text()
        low_head: str = dialog.low_edit.text()
        high_head: str = dialog.high_edit.text()
        close_head: str = dialog.close_edit.text()
        volume_head: str = dialog.volume_edit.text()
        turnover_head: str = dialog.turnover_edit.text()
        open_interest_head: str = dialog.open_interest_edit.text()
        datetime_format: str = dialog.format_edit.text()

        start, end, count = self.engine.import_data_from_csv(
            file_path,
            symbol,
            exchange,
            interval,
            tz_name,
            datetime_head,
            open_head,
            high_head,
            low_head,
            close_head,
            volume_head,
            turnover_head,
            open_interest_head,
            datetime_format
        )

        msg: str = f"\
        CSV载入成功\n\
        代码：{symbol}\n\
        交易所：{exchange.value}\n\
        周期：{interval.value}\n\
        起始：{start}\n\
        结束：{end}\n\
        总数量：{count}\n\
        "
        QtWidgets.QMessageBox.information(self, "载入成功！", msg)

    def output_data(
            self,
            symbol: str,
            exchange: Exchange,
            interval: Interval,
            start: datetime,
            end: datetime
    ) -> None:
        """"""
        # Get output date range
        dialog: DateRangeDialog = DateRangeDialog(start, end)
        n: int = dialog.exec_()
        if n != dialog.Accepted:
            return
        start, end = dialog.get_date_range()

        # Get output file path
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "导出数据",
            "",
            "CSV(*.csv)"
        )
        if not path:
            return

        result: bool = self.engine.output_data_to_csv(
            path,
            symbol,
            exchange,
            interval,
            start,
            end
        )

        if not result:
            QtWidgets.QMessageBox.warning(
                self,
                "导出失败！",
                "该文件已在其他程序中打开，请关闭相关程序后再尝试导出数据。"
            )

    def show_data(
            self,
            symbol: str,
            exchange: Exchange,
            interval: Interval,
            start: datetime,
            end: datetime
    ) -> None:
        """"""
        # Get output date range
        dialog: DateRangeDialog = DateRangeDialog(start, end)
        n: int = dialog.exec_()
        if n != dialog.Accepted:
            return
        start, end = dialog.get_date_range()

        bars: List[BarData] = self.engine.load_bar_data(
            symbol,
            exchange,
            interval,
            start,
            end
        )

        self.table.setRowCount(0)
        self.table.setRowCount(len(bars))

        for row, bar in enumerate(bars):
            self.table.setItem(row, 0, DataCell(bar.datetime.strftime("%Y-%m-%d %H:%M:%S")))
            self.table.setItem(row, 1, DataCell(str(bar.open_price)))
            self.table.setItem(row, 2, DataCell(str(bar.high_price)))
            self.table.setItem(row, 3, DataCell(str(bar.low_price)))
            self.table.setItem(row, 4, DataCell(str(bar.close_price)))
            self.table.setItem(row, 5, DataCell(str(bar.volume)))
            self.table.setItem(row, 6, DataCell(str(bar.turnover)))
            self.table.setItem(row, 7, DataCell(str(bar.open_interest)))

    def delete_data(
            self,
            symbol: str,
            exchange: Exchange,
            interval: Interval
    ) -> None:
        """"""
        n = QtWidgets.QMessageBox.warning(
            self,
            "删除确认",
            f"请确认是否要删除{symbol} {exchange.value} {interval.value}的全部数据",
            QtWidgets.QMessageBox.Ok,
            QtWidgets.QMessageBox.Cancel
        )

        if n == QtWidgets.QMessageBox.Cancel:
            return

        count: int = self.engine.delete_bar_data(
            symbol,
            exchange,
            interval
        )
        self.refresh_tree()  # 添加删除自动刷新
        QtWidgets.QMessageBox.information(
            self,
            "删除成功",
            f"已删除{symbol} {exchange.value} {interval.value}共计{count}条数据",
            QtWidgets.QMessageBox.Ok
        )

    def update_data(self) -> None:
        """"""
        overviews: List[BarOverview] = self.engine.get_bar_overview()
        total: int = len(overviews)
        count: int = 0

        dialog: QtWidgets.QProgressDialog = QtWidgets.QProgressDialog(
            "历史数据更新中",
            "取消",
            0,
            100
        )
        dialog.setWindowTitle("更新进度")
        dialog.setWindowModality(QtCore.Qt.WindowModal)
        dialog.setValue(0)

        for overview in overviews:
            if dialog.wasCanceled():
                break

            self.engine.download_bar_data(
                overview.symbol,
                overview.exchange,
                overview.interval,
                overview.end,
                self.output
            )
            count += 1
            progress = int(round(count / total * 100, 0))
            dialog.setValue(progress)

        dialog.close()

    def download_data(self) -> None:
        """"""
        dialog: DownloadDialog = DownloadDialog(self.engine)
        dialog.exec_()

    def show(self) -> None:
        """"""
        self.showMaximized()

    def output(self, msg: str) -> None:
        """输出下载过程中的日志"""
        QtWidgets.QMessageBox.warning(
            self,
            "数据下载",
            msg,
            QtWidgets.QMessageBox.Ok,
            QtWidgets.QMessageBox.Ok,
        )


class DataCell(QtWidgets.QTableWidgetItem):
    """"""

    def __init__(self, text: str = "") -> None:
        super().__init__(text)

        self.setTextAlignment(QtCore.Qt.AlignCenter)


class DateRangeDialog(QtWidgets.QDialog):
    """"""

    def __init__(self, start: datetime, end: datetime, parent=None) -> None:
        """"""
        super().__init__(parent)

        self.setWindowTitle("选择数据区间")

        self.start_edit: QtWidgets.QDateEdit = QtWidgets.QDateEdit(
            QtCore.QDate(
                start.year,
                start.month,
                start.day
            )
        )
        self.end_edit: QtWidgets.QDateEdit = QtWidgets.QDateEdit(
            QtCore.QDate(
                end.year,
                end.month,
                end.day
            )
        )

        button: QtWidgets.QPushButton = QtWidgets.QPushButton("确定")
        button.clicked.connect(self.accept)

        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow("开始时间", self.start_edit)
        form.addRow("结束时间", self.end_edit)
        form.addRow(button)

        self.setLayout(form)

    def get_date_range(self) -> Tuple[datetime, datetime]:
        """"""
        start = self.start_edit.dateTime().toPython()
        end = self.end_edit.dateTime().toPython() + timedelta(days=1)
        return start, end


class ImportDialog(QtWidgets.QDialog):
    """"""

    def __init__(self, parent=None) -> None:
        """"""
        super().__init__()

        self.setWindowTitle("从CSV文件导入数据")
        self.setFixedWidth(300)

        self.setWindowFlags(
            (self.windowFlags() | QtCore.Qt.CustomizeWindowHint)
            & ~QtCore.Qt.WindowMaximizeButtonHint)

        file_button: QtWidgets.QPushButton = QtWidgets.QPushButton("选择文件")
        file_button.clicked.connect(self.select_file)

        load_button: QtWidgets.QPushButton = QtWidgets.QPushButton("确定")
        load_button.clicked.connect(self.accept)

        self.file_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.symbol_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()

        self.exchange_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        for i in Exchange:
            self.exchange_combo.addItem(str(i.name), i)

        self.interval_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        for i in Interval:
            if i != Interval.TICK:
                self.interval_combo.addItem(str(i.name), i)

        self.tz_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.tz_combo.addItems(available_timezones())
        self.tz_combo.setCurrentIndex(self.tz_combo.findText("Asia/Shanghai"))

        self.datetime_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("datetime")
        self.open_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("open")
        self.high_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("high")
        self.low_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("low")
        self.close_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("close")
        self.volume_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("volume")
        self.turnover_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("turnover")
        self.open_interest_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("open_interest")

        self.format_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("%Y-%m-%d %H:%M:%S")

        info_label: QtWidgets.QLabel = QtWidgets.QLabel("合约信息")
        info_label.setAlignment(QtCore.Qt.AlignCenter)

        head_label: QtWidgets.QLabel = QtWidgets.QLabel("表头信息")
        head_label.setAlignment(QtCore.Qt.AlignCenter)

        format_label: QtWidgets.QLabel = QtWidgets.QLabel("格式信息")
        format_label.setAlignment(QtCore.Qt.AlignCenter)

        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow(file_button, self.file_edit)
        form.addRow(QtWidgets.QLabel())
        form.addRow(info_label)
        form.addRow("代码", self.symbol_edit)
        form.addRow("交易所", self.exchange_combo)
        form.addRow("周期", self.interval_combo)
        form.addRow("时区", self.tz_combo)
        form.addRow(QtWidgets.QLabel())
        form.addRow(head_label)
        form.addRow("时间戳", self.datetime_edit)
        form.addRow("开盘价", self.open_edit)
        form.addRow("最高价", self.high_edit)
        form.addRow("最低价", self.low_edit)
        form.addRow("收盘价", self.close_edit)
        form.addRow("成交量", self.volume_edit)
        form.addRow("成交额", self.turnover_edit)
        form.addRow("持仓量", self.open_interest_edit)
        form.addRow(QtWidgets.QLabel())
        form.addRow(format_label)
        form.addRow("时间格式", self.format_edit)
        form.addRow(QtWidgets.QLabel())
        form.addRow(load_button)

        self.setLayout(form)

    def select_file(self) -> None:
        """"""
        result: str = QtWidgets.QFileDialog.getOpenFileName(
            self, filter="CSV (*.csv)")
        filename: str = result[0]
        if filename:
            self.file_edit.setText(filename)


class DownloadDialog(QtWidgets.QDialog):
    """下载数据"""

    def __init__(self, engine: ManagerEngine, parent=None) -> None:
        """"""
        super().__init__()

        self.engine: ManagerEngine = engine

        self.setWindowTitle("下载历史数据")
        self.setFixedWidth(300)

        self.setWindowFlags(
            (self.windowFlags() | QtCore.Qt.CustomizeWindowHint)
            & ~QtCore.Qt.WindowMaximizeButtonHint)

        self.symbol_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()

        self.exchange_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        for i in Exchange:
            self.exchange_combo.addItem(str(i.name), i)

        self.interval_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        for i in Interval:
            self.interval_combo.addItem(str(i.name), i)

        end_dt: datetime = datetime.now()
        start_dt: datetime = end_dt - timedelta(days=3 * 365)

        self.start_date_edit: QtWidgets.QDateEdit = QtWidgets.QDateEdit(
            QtCore.QDate(
                start_dt.year,
                start_dt.month,
                start_dt.day
            )
        )

        button: QtWidgets.QPushButton = QtWidgets.QPushButton("下载")
        button.clicked.connect(self.download)

        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow("代码", self.symbol_edit)
        form.addRow("交易所", self.exchange_combo)
        form.addRow("周期", self.interval_combo)
        form.addRow("开始日期", self.start_date_edit)
        form.addRow(button)

        self.setLayout(form)

    def download(self) -> None:
        """点击下载"""
        symbol: str = self.symbol_edit.text()
        exchange: Exchange = Exchange(self.exchange_combo.currentData())
        interval: Interval = Interval(self.interval_combo.currentData())

        start_date = self.start_date_edit.date()
        start: datetime = datetime(start_date.year(), start_date.month(), start_date.day())
        start: datetime = start.replace(tzinfo=DB_TZ)

        if interval == Interval.TICK:
            count: int = self.engine.download_tick_data(symbol, exchange, start, self.output)
        else:
            count: int = self.engine.download_bar_data(symbol, exchange, interval, start, self.output)  # 调用数据库管理引擎

        QtWidgets.QMessageBox.information(self, "下载结束", f"下载总数据量：{count}条")

    def output(self, msg: str) -> None:
        """输出下载过程中的日志"""
        QtWidgets.QMessageBox.warning(
            self,
            "数据下载",
            msg,
            QtWidgets.QMessageBox.Ok,
            QtWidgets.QMessageBox.Ok,
        )