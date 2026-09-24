from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import math
import subprocess

root=Path(__file__).resolve().parents[1]
docs=root/'docs'
font_path='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
font_bold='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
pdfmetrics.registerFont(TTFont('DejaVuSerif',font_path))
pdfmetrics.registerFont(TTFont('DejaVuSerif-Bold',font_bold))

# ER diagram using Graphviz for clean orthogonal connectors and readable Russian labels.
dot=docs/'er_diagram.dot'
dot.write_text(r'''digraph G {
  graph [rankdir=LR, splines=ortho, nodesep=0.5, ranksep=1.0, bgcolor="white", pad=0.2, fontname="DejaVu Serif"];
  node [shape=plain, fontname="DejaVu Serif"];
  edge [color="#111111", penwidth=1.2, arrowsize=0.7];

  users [label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6" BGCOLOR="#eafaf2"><TR><TD BGCOLOR="#00FA9A"><B>users</B></TD></TR><TR><TD ALIGN="LEFT">PK user_id</TD></TR><TR><TD ALIGN="LEFT">full_name</TD></TR><TR><TD ALIGN="LEFT">login UNIQUE</TD></TR><TR><TD ALIGN="LEFT">password_hash</TD></TR><TR><TD ALIGN="LEFT">role</TD></TR></TABLE>>];
  suppliers [label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6"><TR><TD BGCOLOR="#7FFF00"><B>suppliers</B></TD></TR><TR><TD ALIGN="LEFT">PK supplier_id</TD></TR><TR><TD ALIGN="LEFT">name UNIQUE</TD></TR></TABLE>>];
  manufacturers [label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6"><TR><TD BGCOLOR="#7FFF00"><B>manufacturers</B></TD></TR><TR><TD ALIGN="LEFT">PK manufacturer_id</TD></TR><TR><TD ALIGN="LEFT">name UNIQUE</TD></TR></TABLE>>];
  categories [label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6"><TR><TD BGCOLOR="#7FFF00"><B>categories</B></TD></TR><TR><TD ALIGN="LEFT">PK category_id</TD></TR><TR><TD ALIGN="LEFT">name UNIQUE</TD></TR></TABLE>>];
  labels [label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6"><TR><TD BGCOLOR="#7FFF00"><B>labels</B></TD></TR><TR><TD ALIGN="LEFT">PK label_id</TD></TR><TR><TD ALIGN="LEFT">name UNIQUE</TD></TR></TABLE>>];
  record_formats [label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6"><TR><TD BGCOLOR="#7FFF00"><B>record_formats</B></TD></TR><TR><TD ALIGN="LEFT">PK format_id</TD></TR><TR><TD ALIGN="LEFT">name UNIQUE</TD></TR></TABLE>>];
  products [label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5"><TR><TD BGCOLOR="#00FA9A"><B>products</B></TD></TR><TR><TD ALIGN="LEFT">PK product_id</TD></TR><TR><TD ALIGN="LEFT">article UNIQUE</TD></TR><TR><TD ALIGN="LEFT">name</TD></TR><TR><TD ALIGN="LEFT">artist</TD></TR><TR><TD ALIGN="LEFT">FK category_id</TD></TR><TR><TD ALIGN="LEFT">FK label_id</TD></TR><TR><TD ALIGN="LEFT">FK manufacturer_id</TD></TR><TR><TD ALIGN="LEFT">FK supplier_id</TD></TR><TR><TD ALIGN="LEFT">FK format_id</TD></TR><TR><TD ALIGN="LEFT">unit</TD></TR><TR><TD ALIGN="LEFT">price</TD></TR><TR><TD ALIGN="LEFT">stock_quantity</TD></TR><TR><TD ALIGN="LEFT">discount</TD></TR><TR><TD ALIGN="LEFT">description</TD></TR><TR><TD ALIGN="LEFT">image_path</TD></TR><TR><TD ALIGN="LEFT">is_new / is_bestseller / is_staff_pick</TD></TR><TR><TD ALIGN="LEFT">is_preorder / is_color_vinyl</TD></TR><TR><TD ALIGN="LEFT">created_at</TD></TR></TABLE>>];
  pickup_points [label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6"><TR><TD BGCOLOR="#7FFF00"><B>pickup_points</B></TD></TR><TR><TD ALIGN="LEFT">PK pickup_point_id</TD></TR><TR><TD ALIGN="LEFT">address UNIQUE</TD></TR></TABLE>>];
  orders [label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6"><TR><TD BGCOLOR="#00FA9A"><B>orders</B></TD></TR><TR><TD ALIGN="LEFT">PK order_id</TD></TR><TR><TD ALIGN="LEFT">order_number UNIQUE</TD></TR><TR><TD ALIGN="LEFT">FK client_id</TD></TR><TR><TD ALIGN="LEFT">FK pickup_point_id</TD></TR><TR><TD ALIGN="LEFT">order_date</TD></TR><TR><TD ALIGN="LEFT">delivery_date</TD></TR><TR><TD ALIGN="LEFT">pickup_code</TD></TR><TR><TD ALIGN="LEFT">status</TD></TR></TABLE>>];
  order_items [label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6"><TR><TD BGCOLOR="#00FA9A"><B>order_items</B></TD></TR><TR><TD ALIGN="LEFT">PK order_item_id</TD></TR><TR><TD ALIGN="LEFT">FK order_id</TD></TR><TR><TD ALIGN="LEFT">FK product_id</TD></TR><TR><TD ALIGN="LEFT">quantity</TD></TR><TR><TD ALIGN="LEFT">unit_price</TD></TR><TR><TD ALIGN="LEFT">UNIQUE(order_id, product_id)</TD></TR></TABLE>>];

  suppliers -> products [label="1:N", fontname="DejaVu Serif", fontsize=9];
  manufacturers -> products [label="1:N", fontname="DejaVu Serif", fontsize=9];
  categories -> products [label="1:N", fontname="DejaVu Serif", fontsize=9];
  labels -> products [label="1:N", fontname="DejaVu Serif", fontsize=9];
  record_formats -> products [label="1:N", fontname="DejaVu Serif", fontsize=9];
  users -> orders [label="1:N", fontname="DejaVu Serif", fontsize=9];
  pickup_points -> orders [label="1:N", fontname="DejaVu Serif", fontsize=9];
  products -> order_items [label="1:N", fontname="DejaVu Serif", fontsize=9];
  orders -> order_items [label="1:N", fontname="DejaVu Serif", fontsize=9];
}
''',encoding='utf-8')
subprocess.run(['dot','-Tpdf',str(dot),'-o',str(docs/'er_diagram.pdf')],check=True)

# Algorithm flowchart - compact one-page Graphviz scheme.
alg_dot = docs / 'module2_algorithm.dot'
alg_pdf = docs / 'module2_algorithm.pdf'
alg_text = r"""digraph A {
  graph [rankdir=TB, splines=ortho, nodesep=0.35, ranksep=0.45, pad=0.15,
         bgcolor="white", fontname="DejaVu Serif", labelloc="t",
         label="USTUJ RECORDS - БЛОК-СХЕМА АЛГОРИТМА ПРИЛОЖЕНИЯ\n\nСхема отражает запуск, авторизацию, гостевой режим, роли и основные функции. Символы: начало/конец, процесс, ввод/вывод, решение. Подготовлено по смыслу ГОСТ 19.701-90.", fontsize=15];
  node [fontname="DejaVu Serif", fontsize=9.5, color="#111111", penwidth=1.15, style="filled", fillcolor="white", margin="0.10,0.06"];
  edge [fontname="DejaVu Serif", fontsize=7.5, color="#111111", penwidth=1.0, arrowsize=0.65];

  start [shape=oval, fillcolor="#00FA9A", label="НАЧАЛО"];
  launch [shape=box, label="Запустить приложение\nи подключиться к БД"];
  login_screen [shape=parallelogram, label="Показать окно входа"];
  has_credentials [shape=diamond, fillcolor="#7FFF00", label="Есть\nлогин и пароль?"];
  guest_catalog [shape=box, fillcolor="#FFD72A", label="Открыть каталог гостя\nбез поиска, сортировки и фильтрации"];
  auth_check [shape=box, label="Проверить логин и пароль\nв БД"];
  auth_success [shape=diamond, fillcolor="#7FFF00", label="Авторизация\nуспешна?"];
  auth_error [shape=box, fillcolor="#FFD8D6", label="Вывести информативное\nсообщение об ошибке"];
  role [shape=diamond, fillcolor="#7FFF00", label="Определить роль\nклиент / менеджер / администратор"];
  client_catalog [shape=box, label="Клиент:\nпросмотр товаров без\nпоиска/сортировки/фильтрации"];
  manager_catalog [shape=box, label="Менеджер:\nпросмотр товаров +\nпоиск, сортировка, фильтр"];
  manager_orders [shape=box, label="Менеджер:\nпросмотр заказов"];
  admin_catalog [shape=box, label="Администратор:\nпросмотр товаров + поиск,\nсортировка, фильтр"];
  admin_product_crud [shape=box, label="Администратор:\nдобавление / редактирование /\nудаление товаров"];
  admin_order_crud [shape=box, label="Администратор:\nпросмотр / добавление /\nредактирование / удаление заказов"];
  output [shape=parallelogram, label="Вывести товары из БД:\nфото или picture.png, название, категория,\nописание, цена, скидка, остаток"];
  logout [shape=diamond, fillcolor="#7FFF00", label="Нажата команда\n«Выйти»?"];
  login_again [shape=parallelogram, label="Вернуться на окно входа"];
  end [shape=oval, fillcolor="#00FA9A", label="КОНЕЦ"];

  start -> launch -> login_screen -> has_credentials;
  has_credentials -> auth_check [label="да"];
  has_credentials -> guest_catalog [label="нет"];
  guest_catalog -> output;
  auth_check -> auth_success;
  auth_success -> auth_error [label="нет"];
  auth_error -> login_screen [label="повторить"];
  auth_success -> role [label="да"];
  role -> client_catalog [label="клиент"];
  role -> manager_catalog [label="менеджер"];
  role -> admin_catalog [label="администратор"];
  manager_catalog -> manager_orders;
  admin_catalog -> admin_product_crud -> admin_order_crud;
  client_catalog -> output;
  manager_orders -> output;
  admin_order_crud -> output;
  output -> logout;
  logout -> login_again [label="да"];
  login_again -> login_screen;
  logout -> end [label="нет"];
}
"""
alg_dot.write_text(alg_text, encoding='utf-8')
subprocess.run(['dot','-Tpdf',str(alg_dot),'-o',str(alg_pdf)], check=True)
print('updated', alg_pdf)
