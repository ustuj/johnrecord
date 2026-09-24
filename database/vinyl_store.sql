PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- Структура БД
CREATE TABLE categories (
	category_id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	PRIMARY KEY (category_id), 
	UNIQUE (name)
);
CREATE TABLE labels (
	label_id INTEGER NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	PRIMARY KEY (label_id), 
	UNIQUE (name)
);
CREATE TABLE manufacturers (
	manufacturer_id INTEGER NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	PRIMARY KEY (manufacturer_id), 
	UNIQUE (name)
);
CREATE TABLE record_formats (
	format_id INTEGER NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	PRIMARY KEY (format_id), 
	UNIQUE (name)
);
CREATE TABLE suppliers (
	supplier_id INTEGER NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	PRIMARY KEY (supplier_id), 
	UNIQUE (name)
);
CREATE TABLE users (
	user_id INTEGER NOT NULL, 
	full_name VARCHAR(200) NOT NULL, 
	login VARCHAR(150) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	PRIMARY KEY (user_id), 
	CONSTRAINT ck_user_role CHECK (role IN ('client','manager','admin')), 
	UNIQUE (login)
);
CREATE TABLE pickup_points (
	pickup_point_id INTEGER NOT NULL, 
	address VARCHAR(255) NOT NULL, 
	PRIMARY KEY (pickup_point_id), 
	UNIQUE (address)
);
CREATE TABLE products (
	product_id INTEGER NOT NULL, 
	article VARCHAR(30) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	artist VARCHAR(160) NOT NULL, 
	category_id INTEGER NOT NULL, 
	label_id INTEGER NOT NULL, 
	manufacturer_id INTEGER NOT NULL, 
	supplier_id INTEGER NOT NULL, 
	format_id INTEGER NOT NULL, 
	unit VARCHAR(20) NOT NULL, 
	price NUMERIC(12, 2) NOT NULL, 
	stock_quantity INTEGER NOT NULL, 
	discount INTEGER NOT NULL, 
	description TEXT NOT NULL, 
	image_path VARCHAR(255) NOT NULL, 
	is_new BOOLEAN NOT NULL, 
	is_bestseller BOOLEAN NOT NULL, 
	is_staff_pick BOOLEAN NOT NULL, 
	is_preorder BOOLEAN NOT NULL, 
	is_color_vinyl BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (product_id), 
	CONSTRAINT ck_product_price_nonnegative CHECK (price >= 0), 
	CONSTRAINT ck_product_stock_nonnegative CHECK (stock_quantity >= 0), 
	CONSTRAINT ck_product_discount_range CHECK (discount >= 0 AND discount <= 100), 
	UNIQUE (article), 
	FOREIGN KEY(category_id) REFERENCES categories (category_id) ON DELETE RESTRICT, 
	FOREIGN KEY(label_id) REFERENCES labels (label_id) ON DELETE RESTRICT, 
	FOREIGN KEY(manufacturer_id) REFERENCES manufacturers (manufacturer_id) ON DELETE RESTRICT, 
	FOREIGN KEY(supplier_id) REFERENCES suppliers (supplier_id) ON DELETE RESTRICT, 
	FOREIGN KEY(format_id) REFERENCES record_formats (format_id) ON DELETE RESTRICT
);
CREATE TABLE orders (
	order_id INTEGER NOT NULL, 
	order_number INTEGER NOT NULL, 
	client_id INTEGER NOT NULL, 
	pickup_point_id INTEGER NOT NULL, 
	order_date DATE NOT NULL, 
	delivery_date DATE, 
	pickup_code INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (order_id), 
	CONSTRAINT ck_order_pickup_code_nonnegative CHECK (pickup_code >= 0), 
	CONSTRAINT ck_order_status CHECK (status IN ('new','processing','ready','completed','cancelled')), 
	UNIQUE (order_number), 
	FOREIGN KEY(client_id) REFERENCES users (user_id) ON DELETE RESTRICT, 
	FOREIGN KEY(pickup_point_id) REFERENCES pickup_points (pickup_point_id) ON DELETE RESTRICT
);
CREATE TABLE order_items (
	order_item_id INTEGER NOT NULL, 
	order_id INTEGER NOT NULL, 
	product_id INTEGER NOT NULL, 
	quantity INTEGER NOT NULL, 
	unit_price NUMERIC(12, 2) NOT NULL, 
	PRIMARY KEY (order_item_id), 
	CONSTRAINT uq_order_product UNIQUE (order_id, product_id), 
	CONSTRAINT ck_order_item_quantity_positive CHECK (quantity > 0), 
	CONSTRAINT ck_order_item_unit_price_nonnegative CHECK (unit_price >= 0), 
	FOREIGN KEY(order_id) REFERENCES orders (order_id) ON DELETE CASCADE, 
	FOREIGN KEY(product_id) REFERENCES products (product_id) ON DELETE RESTRICT
);

-- Индексы

-- Данные
INSERT INTO "categories" VALUES(1,'Инди');
INSERT INTO "categories" VALUES(2,'Мат-рок');
INSERT INTO "categories" VALUES(3,'Пост-рок');
INSERT INTO "categories" VALUES(4,'Рок');
INSERT INTO "categories" VALUES(5,'Саундтрек');
INSERT INTO "categories" VALUES(6,'Соул');
INSERT INTO "categories" VALUES(7,'Фанк / электроника');
INSERT INTO "categories" VALUES(8,'Хип-хоп');
INSERT INTO "categories" VALUES(9,'Шугейз');
INSERT INTO "categories" VALUES(10,'Электроника');
INSERT INTO "labels" VALUES(1,'Def Jam');
INSERT INTO "labels" VALUES(2,'Diwphalanx');
INSERT INTO "labels" VALUES(3,'Everloving');
INSERT INTO "labels" VALUES(4,'Inoxia Records');
INSERT INTO "labels" VALUES(5,'Ipecac');
INSERT INTO "labels" VALUES(6,'KNOWER');
INSERT INTO "labels" VALUES(7,'Kill Rock Stars');
INSERT INTO "labels" VALUES(8,'MIDI Creative');
INSERT INTO "labels" VALUES(9,'Machupicchu Industrias');
INSERT INTO "labels" VALUES(10,'Matador');
INSERT INTO "labels" VALUES(11,'Mercury');
INSERT INTO "labels" VALUES(12,'Roc-A-Fella');
INSERT INTO "labels" VALUES(13,'Rostrum');
INSERT INTO "labels" VALUES(14,'Rough Trade');
INSERT INTO "labels" VALUES(15,'Sargent House');
INSERT INTO "labels" VALUES(16,'Southern Lord');
INSERT INTO "labels" VALUES(17,'ToneVendor');
INSERT INTO "labels" VALUES(18,'VAP');
INSERT INTO "labels" VALUES(19,'Warner Music Japan');
INSERT INTO "labels" VALUES(20,'Warp');
INSERT INTO "labels" VALUES(21,'YEAR0001');
INSERT INTO "labels" VALUES(22,'Yamaha Music');
INSERT INTO "manufacturers" VALUES(1,'Classic Press');
INSERT INTO "manufacturers" VALUES(2,'Heavy Press');
INSERT INTO "manufacturers" VALUES(3,'Soundtrack Press');
INSERT INTO "manufacturers" VALUES(4,'West Coast Press');
INSERT INTO "manufacturers" VALUES(5,'Аналог Пресс');
INSERT INTO "manufacturers" VALUES(6,'Инди Пресс');
INSERT INTO "manufacturers" VALUES(7,'Лондон Пресс');
INSERT INTO "manufacturers" VALUES(8,'Норд Пресс');
INSERT INTO "manufacturers" VALUES(9,'Пресс-Лаб');
INSERT INTO "manufacturers" VALUES(10,'Студия Пресс');
INSERT INTO "manufacturers" VALUES(11,'Токио Пресс');
INSERT INTO "record_formats" VALUES(1,'1LP');
INSERT INTO "record_formats" VALUES(2,'2LP');
INSERT INTO "record_formats" VALUES(3,'7 INCH');
INSERT INTO "record_formats" VALUES(4,'BOX SET');
INSERT INTO "suppliers" VALUES(1,'Аналог Дистрибуция');
INSERT INTO "suppliers" VALUES(2,'Винил Маркет');
INSERT INTO "suppliers" VALUES(3,'Классик Винил');
INSERT INTO "suppliers" VALUES(4,'Норд Дистрибуция');
INSERT INTO "suppliers" VALUES(5,'Токио Винил');
INSERT INTO "suppliers" VALUES(6,'Точка Винил');
INSERT INTO "users" VALUES(1,'Устюжанин Александр Евгеньевич','admin','pbkdf2_sha256$180000$cdf1673ec5bc89e8dc1d98a7b4bb0a4c$39cf7b7cd498e62f9a70654c0ea5fb33b6444cf9a7d008da90aafc17dce8c233','admin');
INSERT INTO "users" VALUES(2,'Дэвид Линч','manager','pbkdf2_sha256$180000$815bef75df28f4ae595518b35fd1708b$d34dfb330a80288e3501017bebef131f098a15942b033ad4746adbfde0663a92','manager');
INSERT INTO "users" VALUES(3,'Шадрин Владимир','client','pbkdf2_sha256$180000$1ecea4029b4dad2832f71a7d03089046$fdebc9db8185f768b0a60d9fcfd14be33d12e6af4553209c73c7bbe7bbb189fd','client');
INSERT INTO "pickup_points" VALUES(1,'630001, Россия, г. Новосибирск, ул. Красный проспект, 18');
INSERT INTO "pickup_points" VALUES(2,'630004, Россия, г. Новосибирск, ул. Ленина, 42');
INSERT INTO "pickup_points" VALUES(3,'630005, Россия, г. Новосибирск, ул. Советская, 64');
INSERT INTO "pickup_points" VALUES(4,'630099, Россия, г. Новосибирск, ул. Кирова, 27');
INSERT INTO "pickup_points" VALUES(5,'630007, Россия, г. Новосибирск, ул. Октябрьская, 34');
INSERT INTO "pickup_points" VALUES(6,'630078, Россия, г. Новосибирск, ул. Титова, 18');
INSERT INTO "pickup_points" VALUES(7,'630048, Россия, г. Новосибирск, ул. Немировича-Данченко, 145');
INSERT INTO "pickup_points" VALUES(8,'630090, Россия, г. Новосибирск, ул. Терешковой, 12');
INSERT INTO "pickup_points" VALUES(9,'630091, Россия, г. Новосибирск, ул. Романова, 39');
INSERT INTO "pickup_points" VALUES(10,'630075, Россия, г. Новосибирск, ул. Богдана Хмельницкого, 47');
INSERT INTO "pickup_points" VALUES(11,'630132, Россия, г. Новосибирск, ул. Челюскинцев, 36');
INSERT INTO "pickup_points" VALUES(12,'630102, Россия, г. Новосибирск, ул. Кирова, 110');
INSERT INTO "pickup_points" VALUES(13,'630017, Россия, г. Новосибирск, ул. Военная, 9');
INSERT INTO "pickup_points" VALUES(14,'630112, Россия, г. Новосибирск, ул. Фрунзе, 86');
INSERT INTO "pickup_points" VALUES(15,'630099, Россия, г. Новосибирск, ул. Коммунистическая, 40');
INSERT INTO "pickup_points" VALUES(16,'630049, Россия, г. Новосибирск, ул. Дуси Ковальчук, 77');
INSERT INTO "pickup_points" VALUES(17,'630124, Россия, г. Новосибирск, ул. Есенина, 14');
INSERT INTO "pickup_points" VALUES(18,'630133, Россия, г. Новосибирск, ул. Гоголя, 204');
INSERT INTO "pickup_points" VALUES(19,'630082, Россия, г. Новосибирск, ул. Жуковского, 96');
INSERT INTO "pickup_points" VALUES(20,'630052, Россия, г. Новосибирск, ул. Станционная, 31');
INSERT INTO "pickup_points" VALUES(21,'050000, Казахстан, г. Алматы, ул. Абая, 44');
INSERT INTO "pickup_points" VALUES(22,'050012, Казахстан, г. Алматы, просп. Назарбаева, 121');
INSERT INTO "pickup_points" VALUES(23,'010000, Казахстан, г. Астана, ул. Кунаева, 10');
INSERT INTO "pickup_points" VALUES(24,'010008, Казахстан, г. Астана, просп. Республики, 25');
INSERT INTO "pickup_points" VALUES(25,'220004, Беларусь, г. Минск, ул. Немига, 12');
INSERT INTO "pickup_points" VALUES(26,'220030, Беларусь, г. Минск, просп. Независимости, 18');
INSERT INTO "pickup_points" VALUES(27,'720000, Кыргызстан, г. Бишкек, ул. Киевская, 95');
INSERT INTO "pickup_points" VALUES(28,'720021, Кыргызстан, г. Ош, ул. Курманжан Датка, 43');
INSERT INTO "pickup_points" VALUES(29,'100011, Узбекистан, г. Ташкент, ул. Шота Руставели, 59');
INSERT INTO "pickup_points" VALUES(30,'100084, Узбекистан, г. Ташкент, просп. Амира Темура, 107');
INSERT INTO "pickup_points" VALUES(31,'734000, Таджикистан, г. Душанбе, просп. Рудаки, 33');
INSERT INTO "pickup_points" VALUES(32,'734025, Таджикистан, г. Душанбе, ул. Айни, 17');
INSERT INTO "pickup_points" VALUES(33,'0010, Армения, г. Ереван, ул. Абовяна, 15');
INSERT INTO "pickup_points" VALUES(34,'0015, Армения, г. Ереван, ул. Маштоца, 28');
INSERT INTO "pickup_points" VALUES(35,'AZ1000, Азербайджан, г. Баку, ул. Истиглалият, 27');
INSERT INTO "pickup_points" VALUES(36,'AZ1001, Азербайджан, г. Баку, просп. Нефтяников, 62');
INSERT INTO "products" VALUES(1,'VNL001','Graduation','Kanye West',8,12,9,1,1,'шт.',3490,6,0,'Студийный альбом Kanye West 2007 года.','https://i.ebayimg.com/images/g/Yc0AAeSwGgVp2gbi/s-l1200.jpg',1,1,1,0,0,'2026-09-24 19:27:28.924885');
INSERT INTO "products" VALUES(2,'VNL002','The College Dropout','Kanye West',8,12,9,2,2,'шт.',3990,4,5,'Дебютный студийный альбом Kanye West.','https://shop.parlour-fam.com/cdn/shop/files/0003922_1_bdb46c36-5579-4f8c-a6e4-358e4189984e.jpg?v=1733740555',0,1,0,0,0,'2026-09-24 19:27:28.924890');
INSERT INTO "products" VALUES(3,'VNL003','My Beautiful Dark Twisted Fantasy','Kanye West',8,1,9,1,1,'шт.',4590,5,0,'Студийный альбом Kanye West 2010 года.','https://vinilo.co.uk/cdn/shop/files/Kanye-West-My-Beautiful-Dark-Twisted-Fantasy-CD_530x%402x.jpg?v=1773596108',0,1,1,0,0,'2026-09-24 19:27:28.924892');
INSERT INTO "products" VALUES(4,'VNL004','Late Registration','Kanye West',8,12,9,2,1,'шт.',3290,8,10,'Второй студийный альбом Kanye West 2005 года.','https://levyikkuna.fi/tiedostot/119/kuva/tuote/600/9421.jpg',0,0,1,0,0,'2026-09-24 19:27:28.924893');
INSERT INTO "products" VALUES(5,'VNL005','Unknown Memory','Yung Lean',8,21,8,6,2,'шт.',3790,3,0,'Дебютный полноформатный альбом Yung Lean 2014 года.','https://vinyl-galore.de/at-get-img/391657/1/unknown-memory-limited-edition-magenta-vinyl-yung-lean-lp.jpg',0,1,0,0,1,'2026-09-24 19:27:28.924894');
INSERT INTO "products" VALUES(6,'VNL006','Stranger','Yung Lean',8,21,8,1,1,'шт.',3690,0,7,'Третий студийный альбом Yung Lean 2017 года.','https://townsquare.media/site/812/files/2017/11/Yung-Lean-Stranger-Album-Cover-Full.jpeg?q=75&w=1080',1,1,0,1,0,'2026-09-24 19:27:28.924895');
INSERT INTO "products" VALUES(7,'VNL007','Fantasma','Cornelius',10,19,10,5,1,'шт.',4290,7,0,'Альбом Cornelius 1997 года.','https://i.ebayimg.com/images/g/7BsAAOSwnB9kl63O/s-l1200.jpg',0,1,1,0,0,'2026-09-24 19:27:28.924896');
INSERT INTO "products" VALUES(8,'VNL008','Point','Cornelius',10,10,10,5,1,'шт.',3990,9,8,'Альбом Cornelius 2002 года.','https://i.pinimg.com/736x/40/85/b3/4085b3251c62e2f63d1ffa7ef6f7e9f2.jpg',0,0,1,0,0,'2026-09-24 19:27:28.924897');
INSERT INTO "products" VALUES(9,'VNL009','Sensuous','Cornelius',10,3,10,4,1,'шт.',3890,5,0,'Альбом Cornelius 2006 года.','https://shop.r10s.jp/book/cabinet/8396/4943674298396.jpg',0,0,1,0,1,'2026-09-24 19:27:28.924898');
INSERT INTO "products" VALUES(10,'VNL010','Mellow Waves','Cornelius',10,13,10,4,1,'шт.',4090,11,12,'Альбом Cornelius 2017 года.','https://i.scdn.co/image/ab67616d0000b2739bb81ababd28277b4c7855d4',1,0,0,0,1,'2026-09-24 19:27:28.924899');
INSERT INTO "products" VALUES(11,'VNL011','the book about my idle plot on a vague anxiety','toe',3,9,5,6,1,'шт.',3590,4,0,'Дебютный полноформатный релиз toe 2005 года.','https://assets.st-note.com/production/uploads/images/26327713/picture_pc_bfcd6ae54ebc6ef5f10b363602feae7c.jpg',0,1,1,0,0,'2026-09-24 19:27:28.924900');
INSERT INTO "products" VALUES(12,'VNL012','For Long Tomorrow','toe',3,9,5,6,1,'шт.',3890,6,5,'Второй полноформатный альбом toe 2009 года.','https://us.rarevinyl.com/cdn/shop/files/toe-for-long-tomorrow-opaque-blue-vinyl-us-vinyl-lp-album-record-tsr086-873970_1000x993.jpg?v=1757174616',0,0,1,0,0,'2026-09-24 19:27:28.924901');
INSERT INTO "products" VALUES(13,'VNL013','HEAR YOU','toe',3,9,5,2,1,'шт.',3790,2,9,'Альбом toe 2015 года.','https://topshelf-records.com/cdn/shop/files/136_1500_300.jpg?v=1684816094&width=1445',1,0,0,0,1,'2026-09-24 19:27:28.924902');
INSERT INTO "products" VALUES(14,'VNL014','Pink','Boris',4,16,2,2,1,'шт.',4290,8,0,'Альбом Boris, выпущенный в 2005 году.','https://i.scdn.co/image/ab67616d0000b273728c73f734bfe4c9204304d',0,1,1,0,0,'2026-09-24 19:27:28.924903');
INSERT INTO "products" VALUES(15,'VNL015','Flood','Boris',4,8,2,5,2,'шт.',4590,5,16,'Экспериментальный альбом Boris 2000 года.','https://thirdmanrecords.com/cdn/shop/products/TMR_733_Boris_Flood_Front-01.png?v=1624649320',0,0,1,0,0,'2026-09-24 19:27:28.924904');
INSERT INTO "products" VALUES(16,'VNL016','Noise','Boris',4,15,2,4,1,'шт.',4190,7,3,'Студийный альбом Boris 2014 года.','https://www.progarchives.com/progressive_rock_discography_covers/12562/cover_2021917122023_r.jpeg',0,0,0,0,1,'2026-09-24 19:27:28.924905');
INSERT INTO "products" VALUES(17,'VNL017','Akuma no Uta','Boris',4,2,2,5,1,'шт.',3490,10,0,'Альбом CAPSULE 2006 года.','https://f4.bcbits.com/img/a3007100955_10.jpg',0,1,1,0,1,'2026-09-24 19:27:28.924906');
INSERT INTO "products" VALUES(18,'VNL018','L.D.K. Lounge Designers Killer','CAPSULE',10,22,11,1,1,'шт.',3390,6,6,'Альбом CAPSULE 2005 года.','https://inoxia-rec.com/cdn/shop/products/Christmas_1000x1000.progressive.jpg?v=1668595336',0,0,0,0,0,'2026-09-24 19:27:28.924907');
INSERT INTO "products" VALUES(19,'VNL019','Smile','Boris',4,4,2,2,1,'шт.',3890,5,0,'Студийный альбом Jockstrap 2022 года.','https://inoxia-rec.com/cdn/shop/products/03_Smile_JK_1000x1000%402x.progressive.jpg?v=1656858026',0,1,1,0,0,'2026-09-24 19:27:28.924908');
INSERT INTO "products" VALUES(20,'VNL020','Wicked City','Jockstrap',1,20,7,6,1,'шт.',3190,8,4,'Мини-альбом Jockstrap 2020 года.','https://i.scdn.co/image/ab67616d0000b27394e482eb4550bebed9f9b524',0,0,0,0,1,'2026-09-24 19:27:28.924909');
INSERT INTO "products" VALUES(21,'VNL021','I<3UQTINVU','Jockstrap',1,14,7,2,1,'шт.',3690,0,20,'Альбом Jockstrap 2021 года.','https://f4.bcbits.com/img/0028963529_71.jpg',1,0,1,1,0,'2026-09-24 19:27:28.924910');
INSERT INTO "products" VALUES(22,'VNL022','Life','KNOWER',7,6,4,1,1,'шт.',3790,6,0,'Альбом KNOWER, доступный на Spotify как Life.','https://miro.medium.com/v2/resize%3Afit%3A700/1%2AlJ_5oj3Vs7NkMgrB5PeTLg.jpeg',0,1,0,0,0,'2026-09-24 19:27:28.924911');
INSERT INTO "products" VALUES(23,'VNL023','KNOWER FOREVER','KNOWER',7,6,4,4,1,'шт.',3990,4,11,'Альбом KNOWER 2023 года.','https://ondarock.it/images/cover/a4133899070_10_1696841571.jpg',1,1,1,0,1,'2026-09-24 19:27:28.924912');
INSERT INTO "products" VALUES(24,'VNL024','Hold Your Horse Is','Hella',2,7,6,6,1,'шт.',3290,5,0,'Дебютный полноформатный альбом Hella 2002 года.','https://http2.mlstatic.com/D_NQ_NP_794513-MLC88967106283_072025-O.webp',0,1,1,0,0,'2026-09-24 19:27:28.924913');
INSERT INTO "products" VALUES(25,'VNL025','There''s No 666 in Outer Space','Hella',2,5,6,1,1,'шт.',3490,3,8,'Альбом Hella 2007 года.','https://f4.bcbits.com/img/a0740065418_10.jpg',0,0,0,0,0,'2026-09-24 19:27:28.924914');
INSERT INTO "products" VALUES(26,'VNL026','Tripper','Hella',2,15,6,2,1,'шт.',3590,9,0,'Альбом Hella 2011 года.','https://f4.bcbits.com/img/a3109220247_10.jpg',1,0,1,0,0,'2026-09-24 19:27:28.924915');
INSERT INTO "products" VALUES(27,'VNL027','Drop You Vivid Colours','Luminous Orange',9,17,11,5,1,'шт.',3390,5,14,'Альбом Luminous Orange 2002 года.','https://cdn.albumoftheyear.org/artists/luminous-orange_1751348753.jpg',0,0,1,0,1,'2026-09-24 19:27:28.924916');
INSERT INTO "products" VALUES(28,'VNL028','PLAYER','CAPSULE',10,22,11,6,1,'шт.',3290,4,0,'Альбом CAPSULE 2008 года.','https://ogre.natalie.mu/media/news/music/2010/0303/capsule_player.jpg?imdensity=1&impolicy=m&imwidth=750',0,1,0,0,0,'2026-09-24 19:27:28.924917');
INSERT INTO "products" VALUES(29,'VNL029','Only You','The Platters',6,11,1,3,1,'шт.',2890,12,5,'Альбом The Platters, выпущенный в 1956 году.','https://1265745076.rsc.cdn77.org/1024/jpg/42667-6245f13650e9a.jpg',0,1,1,0,0,'2026-09-24 19:27:28.924918');
INSERT INTO "products" VALUES(30,'VNL030','CODE: The Price of Wishes','Yugo Kanno',5,18,3,3,2,'шт.',4190,3,0,'Саундтрек Yugo Kanno из серии CODE Geass: Lelouch of the Resurrection.','https://akibashipping.com/cdn/shop/products/B0CG1J95HR_1_df359d1b-21df-4743-84cd-41bca0188638_1200x1200.jpg?v=1700542706',0,1,1,0,0,'2026-09-24 19:27:28.924919');
INSERT INTO "orders" VALUES(1,1,3,1,'2026-02-10','2026-02-14',901,'completed');
INSERT INTO "orders" VALUES(2,2,3,2,'2026-02-12','2026-02-16',902,'completed');
INSERT INTO "orders" VALUES(3,3,3,21,'2026-02-15','2026-02-19',903,'completed');
INSERT INTO "orders" VALUES(4,4,3,22,'2026-02-18','2026-02-22',904,'completed');
INSERT INTO "orders" VALUES(5,5,3,3,'2026-02-20','2026-02-24',905,'completed');
INSERT INTO "orders" VALUES(6,6,3,25,'2026-02-23','2026-02-27',906,'completed');
INSERT INTO "orders" VALUES(7,7,3,7,'2026-03-01','2026-03-05',907,'completed');
INSERT INTO "orders" VALUES(8,8,3,27,'2026-03-03','2026-03-07',908,'new');
INSERT INTO "orders" VALUES(9,9,3,29,'2026-03-06','2026-03-10',909,'new');
INSERT INTO "orders" VALUES(10,10,3,33,'2026-03-08','2026-03-12',910,'new');
INSERT INTO "order_items" VALUES(1,1,1,2,3210.8);
INSERT INTO "order_items" VALUES(2,1,2,2,2870.4);
INSERT INTO "order_items" VALUES(3,2,3,1,3267.6);
INSERT INTO "order_items" VALUES(4,2,4,1,3094.3);
INSERT INTO "order_items" VALUES(5,3,5,10,2594.7);
INSERT INTO "order_items" VALUES(6,3,6,10,3775.2);
INSERT INTO "order_items" VALUES(7,4,7,5,3322.2);
INSERT INTO "order_items" VALUES(8,4,8,4,3025.8);
INSERT INTO "order_items" VALUES(9,5,1,2,3210.8);
INSERT INTO "order_items" VALUES(10,5,2,2,2870.4);
INSERT INTO "order_items" VALUES(11,6,3,1,3267.6);
INSERT INTO "order_items" VALUES(12,6,4,1,3094.3);
INSERT INTO "order_items" VALUES(13,7,5,10,2594.7);
INSERT INTO "order_items" VALUES(14,7,6,10,3775.2);
INSERT INTO "order_items" VALUES(15,8,7,5,3322.2);
INSERT INTO "order_items" VALUES(16,8,8,4,3025.8);
INSERT INTO "order_items" VALUES(17,9,9,5,2456.5);
INSERT INTO "order_items" VALUES(18,9,10,1,2935.5);
INSERT INTO "order_items" VALUES(19,10,11,5,2253.3);
INSERT INTO "order_items" VALUES(20,10,12,5,3750.6);

COMMIT;
