--
-- PostgreSQL database dump
--

\restrict JP5541TJw27JIj9MCerJEsMB2h6iq7t0az1iMJKSlTc3DvWfup34DaRYWcg7yl9

-- Dumped from database version 17.2
-- Dumped by pg_dump version 17.7 (Ubuntu 17.7-3.pgdg24.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.alembic_version (version_num) FROM stdin;
52ce096d0c9d
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.users (username, email, full_name, institution, is_active, role, id, created_at, updated_at, deleted_at, is_deleted, otp, otp_time, is_store_owner) FROM stdin;
Japheth	techwithkhalid247@gmail.com	Japheth	Olabisi Onabanjo University, Ago Iwoye	t	user	67f9936c-38bd-40f3-a86b-ed778d9dcc12	2026-03-05 00:39:44.078931+00	2026-03-05 00:52:23.044783+00	\N	f	\N	\N	f
Afowebdev	cornoladecorneladelimited@gmail.com	Afolabi Mubarak	Olabisi Onabanjo University	t	admin	57bf6bb6-022a-4d43-8b09-93a06852df5f	2025-12-14 11:49:14.7993+00	2025-12-14 11:51:26.757021+00	\N	f	\N	\N	f
elegida_soy	theregalelegida@gmail.com	Elegida	Olabisi Onabanjo University, Ago Iwoye	t	vendor	132c3485-4922-4c81-855f-f0032e42cb2d	2026-03-06 21:17:40.343379+00	2026-03-06 21:19:19.947723+00	\N	f	\N	\N	t
vvictorious	vvictorious9@gmail.com	Victorious Victor	Olabisi Onabanjo University, Ago Iwoye	t	vendor	7d5a6e34-8cde-4dcf-9526-f7f4dcab93e8	2025-12-05 20:57:33.141709+00	2026-01-19 09:37:01.301265+00	\N	f	\N	\N	f
TeslaOS	Ajayihabeeb977@gmail.com	Habeeb Ajayi	Olabisi Onabanjo University, Ago Iwoye	t	vendor	edb57915-aa96-41d1-93c5-ab2655d9db60	2026-01-14 01:27:09.06061+00	2026-01-14 02:23:17.207785+00	\N	f	\N	\N	f
Shami	sham@gmail.com	Okon Patrick	Olabisi Onabanjo University, Ago Iwoye	t	vendor	901dc91a-8326-4bff-8240-4d2a1921b783	2026-03-06 21:35:17.73253+00	2026-03-06 21:35:17.73253+00	\N	f	263872	2026-03-06 22:05:18.526926+00	f
Khalid 	techforme247@gmail.com	Khalid	Obafemi Awolowo University,Ile-Ife	t	vendor	9038937c-ce22-41ea-9219-8d4f3e2b6797	2026-03-05 00:42:22.323051+00	2026-03-12 15:45:30.028905+00	\N	f	\N	\N	t
johndo1e	johndoe@example.com	John Doe	Junio Universty	t	vendor	0c954597-3202-4fa5-b64c-a76cf747befd	2025-12-10 02:03:59.166124+00	2025-12-16 12:20:33.739572+00	\N	f	\N	\N	t
Olawale123	ajayihabeeb977@gmail.com	Olawale Ajayi	Olabisi Onabanjo University	t	vendor	7b882020-08f5-4ae8-890d-30b0f9c1a742	2025-11-24 17:25:54.266297+00	2025-12-19 20:55:51.644121+00	\N	f	\N	\N	t
Kate	kattylarakate@gmail.com	Kate Lara	Olabisi Onabanjo University, Ago Iwoye	t	vendor	f804d142-05f5-4ccb-a6de-0d3150953d58	2026-03-06 21:36:20.408312+00	2026-03-06 21:37:20.629145+00	\N	f	\N	\N	f
Vic	victorogunyemi7@gmail.com	Designer Vic	Olabisi Onabanjo University, Ago Iwoye	t	vendor	a86d5d34-0f9e-4f7f-a213-64799896c15b	2025-11-21 20:51:33.290408+00	2025-11-21 20:53:38.690144+00	\N	f	\N	\N	t
ayo	thingswithkhalid@gmail.com	Ayo deji	University of Abuja, Gwagwalada	t	vendor	19514a0e-be74-4f0d-90e9-e42019772640	2026-03-12 15:53:42.099315+00	2026-03-12 15:54:39.342333+00	\N	f	\N	\N	f
ajadiii	ajadii228@gmail.com	Oludare Abdulazeez	Olabisi Onabanjo University, Ago Iwoye	t	vendor	8f4ef08b-7092-440c-9d03-d5b06101b03a	2025-11-26 13:14:20.72985+00	2026-03-11 13:42:14.749531+00	\N	f	\N	\N	t
corneladeHomes	corneladelimited@gmail.com	Cornelade homes	Olabisi Onabanjo University, Ago Iwoye	t	user	3540a57d-e04b-42f7-a12c-febfe889ed4b	2026-01-15 23:26:45.909365+00	2026-03-12 16:09:19.605535+00	\N	f	\N	\N	f
johndoe	megabytewebnew@gmail.com	Afolabi Mubarak	Olabisi Onabanjo University	t	admin	e1f766c4-77de-4046-83d5-02c029d5ec91	2025-11-14 21:36:00.598594+00	2026-03-01 21:29:11.398446+00	\N	f	\N	\N	f
babatunde	ajayihabeeb997@gmail.com	John Doe	Junio Universty	t	user	778f3002-a0fd-4a76-b8cb-fd3b3301cc74	2025-12-12 21:54:25.371762+00	2025-12-12 21:54:25.371762+00	\N	f	560104	2025-12-12 22:24:26.166929+00	f
olawale	ajayihabeeb999@gmail.com	John Doe	Junio Universty	t	admin	09594ddf-2df6-4e68-a78d-8a2c491ea94c	2025-12-12 21:54:50.542728+00	2025-12-12 21:55:53.420166+00	\N	f	\N	\N	f
afowebdev	afolabimubarak18@gmail.com	 Mubarak Afolabi	Olabisi Onabanjo University, Ago Iwoye	t	vendor	65d34fc0-c3b2-4786-8915-cf3f88c0ba94	2025-11-14 21:21:39.852215+00	2026-03-12 16:52:26.379199+00	\N	f	\N	\N	t
harfoo	afolabimuyideen10@gmail.com	Afolabi Muyideen	University of Abuja, Gwagwalada	t	vendor	93e12f84-592e-4238-b2bb-47131d9ed328	2026-01-15 23:43:03.786462+00	2026-01-15 23:55:37.200137+00	\N	f	\N	\N	f
origamixiii	ogunyemivictor738@gmail.com	Victor Ogunyemi	Olabisi Onabanjo University, Ago Iwoye	t	vendor	d58ab67e-2125-4590-bf3a-dca699db87e9	2026-03-11 13:48:40.967651+00	2026-03-12 17:26:01.233655+00	\N	f	\N	\N	t
\.


--
-- Data for Name: carts; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.carts (user_id, product_id, quantity, id, created_at, updated_at, deleted_at, is_deleted) FROM stdin;
\.


--
-- Data for Name: stores; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.stores (user_id, name, id, created_at, updated_at, deleted_at, is_deleted, is_active, address, phone_number, email, store_logo, store_banner, store_description) FROM stdin;
d58ab67e-2125-4590-bf3a-dca699db87e9	origami store	66cd00e1-1832-4e31-9dd7-179b9caa35ed	2026-03-11 13:49:45.030835+00	2026-03-11 13:49:45.030835+00	\N	f	t	24, Odukalu Somade Street, Oke Alafia, Atikori, Ijebu Igbo	+2348152161484	ogunyemivictor738@gmail.com	\N	\N	\N
65d34fc0-c3b2-4786-8915-cf3f88c0ba94	mubarak afolabi	655e5f63-e7d2-4f58-a677-f92ce108b08e	2025-11-14 21:22:30.458263+00	2025-11-17 23:12:18.898437+00	\N	f	t	5,Kokumo,Crescent	+2348106244890	afolabimubarak18@gmail.com	{"url": "https://res.cloudinary.com/daikgtzat/image/upload/v1763156130/655e5f63-e7d2-4f58-a677-f92ce108b08e/btidp9mku1n4oe9fuztn.jpg", "public_id": "655e5f63-e7d2-4f58-a677-f92ce108b08e/btidp9mku1n4oe9fuztn"}	{"url": "https://res.cloudinary.com/daikgtzat/image/upload/v1763156131/655e5f63-e7d2-4f58-a677-f92ce108b08e/qx2y8tiflnbc1tfbls18.jpg", "public_id": "655e5f63-e7d2-4f58-a677-f92ce108b08e/qx2y8tiflnbc1tfbls18"}	new description testing a new update
a86d5d34-0f9e-4f7f-a213-64799896c15b	mega	54a46d8d-a0e2-4610-a3ca-e1dab5c482ec	2025-11-21 20:52:15.421671+00	2025-11-21 21:37:16.322737+00	\N	f	t	5,Kokumo,Crescent\n5,Kokumo,Crescent	+2348106244890	victorogunyemi7@gmail.com	{"url": "https://res.cloudinary.com/daikgtzat/image/upload/v1763758625/54a46d8d-a0e2-4610-a3ca-e1dab5c482ec/vpellx4yndcrdiqiupui.jpg", "public_id": "54a46d8d-a0e2-4610-a3ca-e1dab5c482ec/vpellx4yndcrdiqiupui"}	{"url": "https://res.cloudinary.com/daikgtzat/image/upload/v1763758627/54a46d8d-a0e2-4610-a3ca-e1dab5c482ec/rimdx7xpvmfjhrmv6dlw.png", "public_id": "54a46d8d-a0e2-4610-a3ca-e1dab5c482ec/rimdx7xpvmfjhrmv6dlw"}	nnnnnnnnnnnnnnnnnnnnnnnnnnnnnn
7b882020-08f5-4ae8-890d-30b0f9c1a742	my awesome store	c0f2f49a-c5c8-4b0e-ac8f-ccbfed153e06	2025-11-24 17:28:43.851319+00	2025-11-24 17:28:43.851319+00	\N	f	t	123, Santos Street, Country	09036977142	ajayihabeeb977@gmail.com	\N	\N	\N
8f4ef08b-7092-440c-9d03-d5b06101b03a	ajadi store	40017d0f-2c8e-43cb-bccf-c79e3952e140	2025-11-26 13:16:38.00465+00	2025-11-26 13:16:38.00465+00	\N	f	t	No 12 Irepodun Street	08128764690	ajadii228@gmail.com	\N	\N	\N
0c954597-3202-4fa5-b64c-a76cf747befd	my awesome stor1e	cefc58e4-a720-40e2-9fe5-ff3efd650252	2025-12-10 02:05:46.694358+00	2025-12-10 02:05:46.694358+00	\N	f	t	123, Santos Street, Country	12345678900	johndoe@example.com	\N	\N	\N
9038937c-ce22-41ea-9219-8d4f3e2b6797	alamversal 	8115d9bf-ff36-4762-8bbf-e87c20a4d31a	2026-03-05 00:43:55.518491+00	2026-03-05 00:49:07.786155+00	\N	f	t	50, Olatomiwa road.	8159461285	techwithkhalid247@gmail.com	{"url": "https://res.cloudinary.com/daikgtzat/image/upload/v1772671750/8115d9bf-ff36-4762-8bbf-e87c20a4d31a/mlovrej1qtpfzjogeaqd.jpg", "public_id": "8115d9bf-ff36-4762-8bbf-e87c20a4d31a/mlovrej1qtpfzjogeaqd"}	{"url": "https://res.cloudinary.com/daikgtzat/image/upload/v1772671750/8115d9bf-ff36-4762-8bbf-e87c20a4d31a/yxir8hq92lyqhwqlhnyh.jpg", "public_id": "8115d9bf-ff36-4762-8bbf-e87c20a4d31a/yxir8hq92lyqhwqlhnyh"}	This is a great store
132c3485-4922-4c81-855f-f0032e42cb2d	soy	57224a25-f30f-4c74-9d7a-5686cdb8ebea	2026-03-06 21:19:18.069296+00	2026-03-06 21:24:19.147763+00	\N	f	t	Remote	+2349069418881	theregalelegida@gmail.com	{"url": "https://res.cloudinary.com/daikgtzat/image/upload/v1772832261/57224a25-f30f-4c74-9d7a-5686cdb8ebea/p0yrcn3dq4hmympbvvel.jpg", "public_id": "57224a25-f30f-4c74-9d7a-5686cdb8ebea/p0yrcn3dq4hmympbvvel"}	{"url": "https://res.cloudinary.com/daikgtzat/image/upload/v1772832262/57224a25-f30f-4c74-9d7a-5686cdb8ebea/ul7uxnng9wt6dp00sm30.jpg", "public_id": "57224a25-f30f-4c74-9d7a-5686cdb8ebea/ul7uxnng9wt6dp00sm30"}	I sell cool things 
\.


--
-- Data for Name: contact_info; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.contact_info (name, title, email, id, created_at, updated_at, deleted_at, is_deleted, store_id, phone_number) FROM stdin;
Mubarak Afolabi	Owner	afolabimubarak18@gmail.com	590d8a87-5aa6-4468-b2de-df3c3d7f7b7f	2025-11-14 21:22:53.701507+00	2025-11-14 21:22:53.701507+00	\N	f	655e5f63-e7d2-4f58-a677-f92ce108b08e	+2348106244890
Khalid	Ceo	techwithkhalid247@gmail.com	33d24a41-953d-4f1e-b4a0-44cbf5c12e16	2026-03-05 00:44:24.499346+00	2026-03-05 00:44:24.499346+00	\N	f	8115d9bf-ff36-4762-8bbf-e87c20a4d31a	8159461285
Elegida 	CEO	theregalelegida@gmail.com	9cb92e05-598f-4267-9282-a1212bc46f10	2026-03-06 21:20:12.501882+00	2026-03-06 21:20:12.501882+00	\N	f	57224a25-f30f-4c74-9d7a-5686cdb8ebea	+2349069418881
\.


--
-- Data for Name: inventories; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.inventories (product_id, available, reserved, id, created_at, updated_at, deleted_at, is_deleted) FROM stdin;
6917ab0cee1e28bf5370c33f	10	0	68c472d6-87c6-41bc-8635-d0ec5c95b086	2025-11-14 22:19:54.722514+00	2025-11-14 22:19:54.722514+00	\N	f
6917ae37ee1e28bf5370c340	2000	0	55584b1e-7269-4187-9849-52867494f167	2025-11-14 22:33:25.680584+00	2025-11-14 22:33:25.680584+00	\N	f
691a3d2c586c3b897bf3e610	10	0	c0d5c1c3-075c-4516-babb-6071259be365	2025-11-16 21:07:54.103398+00	2025-11-16 21:07:54.103398+00	\N	f
691b977e3c4af89b538cf6a3	2	0	d78c97a1-75a8-453a-9aef-b518157c701f	2025-11-17 21:45:32.995423+00	2025-11-17 21:45:32.995423+00	\N	f
6920d2c06ead2a596e29df55	10	0	3237b86a-dcc0-4f12-be24-a591ab86dbbc	2025-11-21 20:59:42.377497+00	2025-11-21 20:59:42.377497+00	\N	f
69295ffdf8c5693a796a3aba	10	0	f8776bf6-1fd3-439c-a7a7-6c41cda70836	2025-11-28 08:40:27.217633+00	2025-11-28 08:40:27.217633+00	\N	f
69296021f8c5693a796a3abb	10	0	0636f23c-f19e-4ea5-b43a-fadf7afde856	2025-11-28 08:41:03.549076+00	2025-11-28 08:41:03.549076+00	\N	f
693c8fc71c06e5729c558959	20	0	3a3fcb34-4c1c-4243-8ae6-4cdc7b980249	2025-12-12 21:57:25.063841+00	2025-12-12 21:57:25.063841+00	\N	f
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.payments (user_id, amount, currency, provider, provider_payment_id, id, created_at, updated_at, deleted_at, is_deleted, status, payment_url) FROM stdin;
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.orders (user_id, total_amount, id, created_at, updated_at, deleted_at, is_deleted, payment_id, products, status, idempotent_key, reference_token, username) FROM stdin;
\.


--
-- Data for Name: suborders; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.suborders (order_id, store_id, total_amount, shipping_fee, otp, id, created_at, updated_at, deleted_at, is_deleted, username, status) FROM stdin;
\.


--
-- Data for Name: order_items; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.order_items (product_id, suborder_id, quantity, product_snapshot, unit_price, line_price, id, created_at, updated_at, deleted_at, is_deleted) FROM stdin;
\.


--
-- Data for Name: payouts_info; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.payouts_info (account_name, store_id, bank_name, account_number, id, created_at, updated_at, deleted_at, is_deleted, security_question, security_answer, withdrawal_pin) FROM stdin;
Mega	655e5f63-e7d2-4f58-a677-f92ce108b08e	gtb	8106244890	7fd8bc3c-278d-44fd-a594-83c3ec99af69	2025-11-14 21:34:32.585821+00	2025-11-14 21:34:32.585821+00	\N	f	What was your first pet’s name?	cat	122333
Mega	54a46d8d-a0e2-4610-a3ca-e1dab5c482ec	gtb	1234566767	f97331f3-3dd7-4a69-8bbb-de44bd301542	2025-11-21 20:56:01.821905+00	2025-11-21 20:56:01.821905+00	\N	f	What was your first pet’s name?	cat	123456
Ajadi	40017d0f-2c8e-43cb-bccf-c79e3952e140	access	1234567890	ac5c2d18-9a95-4fd3-a0a3-3e6c33c5a29d	2025-11-26 13:17:56.681996+00	2025-11-26 13:17:56.681996+00	\N	f	What was your first pet’s name?	ajadi	123456
Khalid jap	8115d9bf-ff36-4762-8bbf-e87c20a4d31a	uba	8159461285	072d9f6e-5665-4f1e-b4d5-c270c348759c	2026-03-05 00:47:24.168313+00	2026-03-05 00:47:24.168313+00	\N	f	What city were you born in?	Ijebu	176060
Soy	57224a25-f30f-4c74-9d7a-5686cdb8ebea	zenith	8367883864	aafba3d3-a65d-4768-acc5-ef12a1d93692	2026-03-06 21:22:00.317557+00	2026-03-06 21:22:00.317557+00	\N	f	What was your first pet’s name?	Mark	123456
Victor	66cd00e1-1832-4e31-9dd7-179b9caa35ed	gtb	0429656737	52da3281-a322-4753-b36e-c5b874afc158	2026-03-11 13:50:49.073733+00	2026-03-11 13:50:49.073733+00	\N	f	What city were you born in?	Ijebu	123456
\.


--
-- Data for Name: refresh_tokens; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.refresh_tokens (user_id, token, device_id, user_agent, ip_address, issued_at, expires_at, id, created_at, updated_at, deleted_at, is_deleted) FROM stdin;
edb57915-aa96-41d1-93c5-ab2655d9db60	5f6bba1275c8f2919c192797786ae85a78bf89b68365c9c7f080e55f0b356d11	c331fc30-700c-4241-b40b-1d4b45afbf80	Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36	102.89.46.35	2026-01-14 02:23:16.615569+00	2026-02-13 02:23:17.926961+00	2d20f151-d445-4488-ae4a-f58230570eb5	2026-01-14 02:23:16.615569+00	2026-01-14 02:23:16.615569+00	\N	f
65d34fc0-c3b2-4786-8915-cf3f88c0ba94	f210091f4aeed53ee127d16e5d56220773464d51256f87e4bf442c3b50d1e729	a7d68413-e84f-4d81-8643-90b770c66703	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36	102.88.113.111	2026-01-15 22:54:14.77851+00	2026-02-14 22:54:18.180035+00	1ee2b8d9-c91f-46df-8a83-dfe716d8b78c	2026-01-15 22:54:14.77851+00	2026-01-15 22:54:14.77851+00	\N	f
e1f766c4-77de-4046-83d5-02c029d5ec91	81c9051e44b50304e2e85a1632e2a61333995bb8184df13d1764301700d0086d	a5965e69-4e1d-4420-a325-6d9a1a37131c	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36	102.88.113.111	2026-01-15 23:00:54.91193+00	2026-02-14 23:00:56.237999+00	371e8a86-97f9-4832-b777-883e45238751	2026-01-15 23:00:54.91193+00	2026-01-15 23:00:54.91193+00	\N	f
3540a57d-e04b-42f7-a12c-febfe889ed4b	4e92acf97a25716ebc02f9a5fa9703c55afe5fe9f2ad5585271781e4bca20f6c	f99ff519-9430-459b-a737-2a468e6729fe	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36	102.88.113.111	2026-01-15 23:27:01.369768+00	2026-02-14 23:27:02.615857+00	d8c21709-eba7-4d34-969d-28ade6131013	2026-01-15 23:27:01.369768+00	2026-01-15 23:27:01.369768+00	\N	f
3540a57d-e04b-42f7-a12c-febfe889ed4b	e7fa1af5be6cf700a25c3d3fcb5d96afff6629edb2760599fc86d4cf403aa8b0	5da69f37-6585-4b4b-86fc-26409098a265	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36	102.88.113.111	2026-01-15 23:27:59.946752+00	2026-02-14 23:28:01.174236+00	3e74f7ce-0cf4-48f9-9c9d-4099124c19e8	2026-01-15 23:27:59.946752+00	2026-01-15 23:27:59.946752+00	\N	f
3540a57d-e04b-42f7-a12c-febfe889ed4b	8aa7e01282df3d3770600c03316dbf50d839953a3febd42f4e72b3a8507e3609	15e543dc-98da-4d78-aff9-ae9e7252833f	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36	102.88.113.111	2026-01-15 23:28:40.856792+00	2026-02-14 23:28:42.106726+00	a6674902-9238-4f4f-969b-ea422c36b0dc	2026-01-15 23:28:40.856792+00	2026-01-15 23:28:40.856792+00	\N	f
65d34fc0-c3b2-4786-8915-cf3f88c0ba94	1d1be1ee122e6ef759a3594f09b6b41aa04d81c8977f664dc2a8d12544bdee2f	1f39cb5d-627c-4efa-8824-4e6edfde136a	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36	102.88.113.111	2026-01-15 23:41:37.7905+00	2026-02-14 23:41:39.942997+00	11036655-4630-4df4-bff3-c2e6d9fccaed	2026-01-15 23:41:37.7905+00	2026-01-15 23:41:37.7905+00	\N	f
93e12f84-592e-4238-b2bb-47131d9ed328	96d7c017795b9114444cb2c17a1fc96e646f465d58928b69fc1aa47c8eca063e	617a841e-ae78-447e-bba9-b74cffd603ee	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36	102.88.113.111	2026-01-15 23:43:29.863025+00	2026-02-14 23:43:31.100994+00	3137d986-47ae-4e89-ae13-9cd8b0256fd2	2026-01-15 23:43:29.863025+00	2026-01-15 23:43:29.863025+00	\N	f
93e12f84-592e-4238-b2bb-47131d9ed328	a0a15ac869202f4bda6416af40347333904ed7a4440cace8d692c0ed7306aa81	f54eaab3-d568-495f-a061-00daee6303ab	Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36	102.88.113.111	2026-01-15 23:55:36.585324+00	2026-02-14 23:55:37.834134+00	5d9ae657-2089-4e38-bd83-4cfb7eb63bc7	2026-01-15 23:55:36.585324+00	2026-01-15 23:55:36.585324+00	\N	f
65d34fc0-c3b2-4786-8915-cf3f88c0ba94	097111bab6471804608a70ace1c4e1cb50737a90b3909bddcec9ba1a429c6e3a	4842122f-4595-40d1-a412-cb707ac0b572	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36	102.88.112.87	2026-01-16 20:17:38.893146+00	2026-02-15 20:17:41.100745+00	40977821-1f62-47ec-b2ff-1b3a12149328	2026-01-16 20:17:38.893146+00	2026-01-16 20:17:38.893146+00	\N	f
3540a57d-e04b-42f7-a12c-febfe889ed4b	5084a4e0965ec381a0900e5690fa9d24c0bf54f59be8d83806fa93869e34e30f	fc12c503-a547-44cf-ad8e-5fe78a2ce238	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36	102.88.112.87	2026-01-16 20:19:36.427011+00	2026-02-15 20:19:37.654988+00	ebb7340a-7d02-425b-a3da-b8b389e1ec73	2026-01-16 20:19:36.427011+00	2026-01-16 20:19:36.427011+00	\N	f
3540a57d-e04b-42f7-a12c-febfe889ed4b	2091542a5a7303594bd1789096daf5ca1c4dcf83cf591fcf63d850a734142c7b	2d7e48bb-324a-446a-af56-361f3176f859	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	102.88.110.55	2026-01-18 20:10:17.251139+00	2026-02-17 20:10:20.203135+00	141f1a82-93ca-4e61-87c7-f68662dd364c	2026-01-18 20:10:17.251139+00	2026-01-18 20:10:17.251139+00	\N	f
7d5a6e34-8cde-4dcf-9526-f7f4dcab93e8	dca849be0c1e385ba02b4e72d1c6a964a7787e378399ef4c040b807e71c4fa5a	402ee343-f94a-4a30-9b2c-cc0a182c1ce1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	102.88.109.173	2026-01-19 09:37:00.714408+00	2026-02-18 09:37:02.288936+00	2e8ca148-cb54-4369-887f-9d23515986a2	2026-01-19 09:37:00.714408+00	2026-01-19 09:37:00.714408+00	\N	f
8f4ef08b-7092-440c-9d03-d5b06101b03a	7940260ae6ee8254b44776d64386e9b7d5c9af7d44c89d575a0bde160548551f	e95e755a-dd2a-45a9-9c2d-2809c1429b45	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36	105.119.10.168	2026-01-20 13:23:23.742831+00	2026-02-19 13:23:27.15599+00	1128a5e0-e100-4748-b087-86ffe13eb9b7	2026-01-20 13:23:23.742831+00	2026-01-20 13:23:23.742831+00	\N	f
65d34fc0-c3b2-4786-8915-cf3f88c0ba94	f61f4223469267bcd2b8e0e1dbdb775b5d4c74b2e03b724970c3adf7a9bcd1eb	8a47c254-2e73-4bd3-9771-c0c035858097	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	102.89.47.147	2026-01-23 20:20:25.842786+00	2026-02-22 20:20:27.994158+00	e8cdf3d5-94f8-4568-9da3-6d50199c6554	2026-01-23 20:20:25.842786+00	2026-01-23 20:20:25.842786+00	\N	f
3540a57d-e04b-42f7-a12c-febfe889ed4b	0ec3c849dcd598b841f954bf5375f5711fc7dc4262705c18b341b5748093ea94	616a4586-126e-4a01-b4f6-5481b389189e	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36	102.89.47.147	2026-01-23 20:21:25.44987+00	2026-02-22 20:21:26.697646+00	fef402a0-f3f1-40ec-8920-e2c0ee20620b	2026-01-23 20:21:25.44987+00	2026-01-23 20:21:25.44987+00	\N	f
65d34fc0-c3b2-4786-8915-cf3f88c0ba94	451db83cc6f4e78704c1e1351f7528dfd8d00fde1ec92fbfdd099389534eb2b3	24a5350b-c0f4-487a-bc1c-88655970ca80	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36	102.89.22.79	2026-03-01 21:22:39.907079+00	2026-03-31 21:22:44.842589+00	1014df08-5a82-4dad-9811-e2ca4e738b08	2026-03-01 21:22:39.907079+00	2026-03-01 21:22:39.907079+00	\N	f
e1f766c4-77de-4046-83d5-02c029d5ec91	493f37b7a43a496902fbefd47f2efd3f72ed30c2b1331839647622bfe1288e09	f484838b-abd1-4655-b142-09600a9d121e	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36	102.89.22.79	2026-03-01 21:27:35.398645+00	2026-03-31 21:27:37.005728+00	dd38217a-6c31-4d15-8a3a-a25c856750d9	2026-03-01 21:27:35.398645+00	2026-03-01 21:27:35.398645+00	\N	f
e1f766c4-77de-4046-83d5-02c029d5ec91	a8030579ed3910f74c9c77edf11451908c6bfb565360f929128cfdd75b35fc18	eefd9e8e-c0dd-4ee4-affd-60482da6d651	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36	102.89.22.79	2026-03-01 21:29:10.787618+00	2026-03-31 21:29:12.037751+00	da8a1935-f287-42f8-bcd9-f8b26edb07ba	2026-03-01 21:29:10.787618+00	2026-03-01 21:29:10.787618+00	\N	f
3540a57d-e04b-42f7-a12c-febfe889ed4b	9de6c4ce15b5eb1d50841e2ea78c540b5707ee4bb7cd6245813e5ce520cd2ef1	f2d2baff-cc80-44e4-8719-c5df752e8fa4	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36	102.89.22.79	2026-03-01 21:29:45.016489+00	2026-03-31 21:29:46.60187+00	3be100d1-d647-4190-903e-e6ff845c1063	2026-03-01 21:29:45.016489+00	2026-03-01 21:29:45.016489+00	\N	f
67f9936c-38bd-40f3-a86b-ed778d9dcc12	f57282e70cb5d04d4e42d0419fcd0cd65d302cee93e80e9af1e496b33a7476aa	45ef4382-ca0e-4d0c-a3a3-99b105a8ab07	Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3 Mobile/15E148 Safari/604.1	197.210.54.193	2026-03-05 00:40:15.939611+00	2026-04-04 00:40:18.895316+00	75c0c271-f3dc-4ab2-bafe-2eac2f74a3fe	2026-03-05 00:40:15.939611+00	2026-03-05 00:40:15.939611+00	\N	f
9038937c-ce22-41ea-9219-8d4f3e2b6797	f70cefce89fd9df028a6e1cbc493417392d1427034bc8cc14714798cf938c1f8	0f87a035-19f8-4728-be42-96d530d139ac	Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3 Mobile/15E148 Safari/604.1	197.210.54.193	2026-03-05 00:42:36.192437+00	2026-04-04 00:42:38.088863+00	7b0837e2-c499-410e-9c95-10c5af28d252	2026-03-05 00:42:36.192437+00	2026-03-05 00:42:36.192437+00	\N	f
67f9936c-38bd-40f3-a86b-ed778d9dcc12	8c26ac8cff34596baac956a5759ba69a4ad0e8061311a3056ab38376d9b9a72d	0fb1e563-0dd1-479f-ac38-7fcfe6cd962a	Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3 Mobile/15E148 Safari/604.1	197.210.54.193	2026-03-05 00:52:22.427321+00	2026-04-04 00:52:23.681629+00	697c39a7-6dcc-4352-bb3c-1f410098ad4c	2026-03-05 00:52:22.427321+00	2026-03-05 00:52:22.427321+00	\N	f
132c3485-4922-4c81-855f-f0032e42cb2d	03fdea147a344c47d4839446038f26f53e9dddc39705dd450ed998dcb89a4cd1	0f9334fd-f2d0-430b-81d3-0350e0e80469	Mozilla/5.0 (iPhone; CPU iPhone OS 15_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/124.0.6367.88 Mobile/15E148 Safari/604.1	102.89.22.141	2026-03-06 21:17:59.517305+00	2026-04-05 21:18:00.772768+00	a60110c9-9472-4f60-a9ab-62ec96d56478	2026-03-06 21:17:59.517305+00	2026-03-06 21:17:59.517305+00	\N	f
3540a57d-e04b-42f7-a12c-febfe889ed4b	2621f0fb95b6b77c7417d67f582d2b7f25b51805f24a353b34167c074bd3d826	16bea871-6b6b-4074-b330-eeb12840e76e	Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36	102.90.97.190	2026-03-09 04:33:46.003889+00	2026-04-08 04:33:47.245029+00	c9125797-bf9f-4c7a-899b-b03a08a0d63b	2026-03-09 04:33:46.003889+00	2026-03-09 04:33:46.003889+00	\N	f
8f4ef08b-7092-440c-9d03-d5b06101b03a	274e8c159bb8b7b43b8707acca838964f118af359b46219cf01acadb9cd25181	423a9a63-8c6f-4433-a81d-8c2dfab39e44	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36	129.222.206.52	2026-03-11 13:42:13.688999+00	2026-04-10 13:42:15.834051+00	0b4ffab3-53be-431f-b219-d04b4ea340c6	2026-03-11 13:42:13.688999+00	2026-03-11 13:42:13.688999+00	\N	f
d58ab67e-2125-4590-bf3a-dca699db87e9	93573905a78540f94d7ec47bd561a09327d08f93f9f66e1ed578d2fc2269dd24	7fa5bf16-bdc6-4d88-9689-3afb4ac0bb17	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36	102.88.110.105	2026-03-11 13:48:52.937273+00	2026-04-10 13:48:54.174748+00	31447d9c-5cf9-437a-bfdd-b393bdf80658	2026-03-11 13:48:52.937273+00	2026-03-11 13:48:52.937273+00	\N	f
d58ab67e-2125-4590-bf3a-dca699db87e9	fe2890f7782326482a0857f8f215ad3ff87ff36b136025fb06feb21292040a71	92474a6c-2402-4f1c-bb65-08af3299f588	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36	102.88.54.176	2026-03-12 16:51:08.834781+00	2026-04-11 16:51:10.989008+00	f1134ccd-91d7-4a7d-92e3-b38ae01acd31	2026-03-12 16:51:08.834781+00	2026-03-12 16:51:08.834781+00	\N	f
65d34fc0-c3b2-4786-8915-cf3f88c0ba94	9688e0cba3a51a134b05bb613903390abd1fdb291f9ae99cb352464f6c8c1e03	89fe322e-efb6-412d-be3d-fef2eb7c240f	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36	102.88.108.32	2026-03-12 16:52:25.312971+00	2026-04-11 16:52:27.46275+00	2e161871-d635-48d8-83c1-a40a21934a32	2026-03-12 16:52:25.312971+00	2026-03-12 16:52:25.312971+00	\N	f
f804d142-05f5-4ccb-a6de-0d3150953d58	2509f07c623bf35a2edbbf7c77336ba711a846e4c82654944f02e55464f1a792	53cb45c4-da7b-437d-b84b-2df9f8a80fa7	Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36	102.89.34.20	2026-03-06 21:37:20.015782+00	2026-04-05 21:37:21.26616+00	2f5a9f5a-65b9-407b-b74d-f48d57888267	2026-03-06 21:37:20.015782+00	2026-03-06 21:37:20.015782+00	\N	f
65d34fc0-c3b2-4786-8915-cf3f88c0ba94	e48ad75a175adbdb24859c1205ffc630f388a575e94c978ff7daa2a51b24936b	95fa9748-31ce-4cdc-90ba-85ec780df7c7	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36	102.88.110.105	2026-03-11 13:46:11.434746+00	2026-04-10 13:46:13.586865+00	7198e2d3-d4b4-4d1f-b2a6-27976f5ff98f	2026-03-11 13:46:11.434746+00	2026-03-11 13:46:11.434746+00	\N	f
3540a57d-e04b-42f7-a12c-febfe889ed4b	41421ba69413c3590d47ea1c69e222edf8194d4aa15dbff5dc8ffb0028e3b9d8	f7cfd911-8117-438a-9105-39b83c13825d	Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36	102.89.45.28	2026-03-11 21:46:02.9984+00	2026-04-10 21:46:04.868511+00	ef197153-34dd-4816-852a-cac9040465e3	2026-03-11 21:46:02.9984+00	2026-03-11 21:46:02.9984+00	\N	f
9038937c-ce22-41ea-9219-8d4f3e2b6797	16d6035e906fd992477d509c54310163cca05dd1600454d38b3f37c9c0d79d48	d49426e0-166d-419f-baac-08bd56e7720e	Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:148.0) Gecko/20100101 Firefox/148.0	102.90.4.6	2026-03-12 15:45:28.969963+00	2026-04-11 15:45:31.20977+00	7defde4d-fd7b-4560-a17a-edf8ef351cde	2026-03-12 15:45:28.969963+00	2026-03-12 15:45:28.969963+00	\N	f
19514a0e-be74-4f0d-90e9-e42019772640	ddfe5d1101b0729080a1768ae4c0a8d0b53e804e19be4aaf2768eb2ca7564054	878515e8-6cbb-4763-8fd1-b44f4d5f9627	Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:148.0) Gecko/20100101 Firefox/148.0	102.90.4.6	2026-03-12 15:54:38.732328+00	2026-04-11 15:54:39.974744+00	8207bbb2-86b9-4788-b29b-0e3cee8d07cc	2026-03-12 15:54:38.732328+00	2026-03-12 15:54:38.732328+00	\N	f
3540a57d-e04b-42f7-a12c-febfe889ed4b	559f8c431b153d8bce47dd4d111512eea041f05120ea8a3a2cc96677534b6af1	b8337835-9e29-4b34-9137-827de86c83ca	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36	102.88.108.32	2026-03-12 16:09:18.991682+00	2026-04-11 16:09:20.242514+00	3efed49c-5f5c-406a-91ee-f8d6fe773f17	2026-03-12 16:09:18.991682+00	2026-03-12 16:09:18.991682+00	\N	f
d58ab67e-2125-4590-bf3a-dca699db87e9	d46652968a28c269daba06954cf5b6de08278d9d258b9966d6d33e4e652d6e68	e81e590f-ea7a-4d11-a239-e2da7587d3d3	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36	102.88.54.176	2026-03-12 17:26:00.183892+00	2026-04-11 17:26:02.320976+00	5f90451d-82fc-44f8-9226-8a28939d5472	2026-03-12 17:26:00.183892+00	2026-03-12 17:26:00.183892+00	\N	f
\.


--
-- Data for Name: shipment_info; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.shipment_info (shipping_address, delivery_method, delivery_fee, delivery_time, id, created_at, updated_at, deleted_at, is_deleted, store_id) FROM stdin;
Door delivery	Standard	10	10	3c776d8d-b0fe-4f92-abce-dd7a7589664d	2025-11-17 22:03:58.669547+00	2025-11-17 22:03:58.669547+00	\N	f	655e5f63-e7d2-4f58-a677-f92ce108b08e
Express	Standard	2000	10	f9ac635d-188a-42bc-9e87-c0c43b1911df	2025-11-17 22:09:37.216169+00	2025-11-17 22:09:37.216169+00	\N	f	655e5f63-e7d2-4f58-a677-f92ce108b08e
Door delivery Service	Standard	0	16	f8ad8abd-2cca-4272-a90f-0f5badd48f06	2025-11-17 22:38:12.284823+00	2025-11-17 22:38:12.284823+00	\N	f	655e5f63-e7d2-4f58-a677-f92ce108b08e
\.


--
-- Data for Name: store_info; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.store_info (id, created_at, updated_at, deleted_at, is_deleted) FROM stdin;
\.


--
-- Data for Name: suborder_snapshots; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.suborder_snapshots (store_id, snapshot_time, total_orders, total_revenue, total_customers, id, created_at, updated_at, deleted_at, is_deleted) FROM stdin;
\.


--
-- Data for Name: verifications; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.verifications (type, user_id, id_number, picture, status, id, created_at, updated_at, deleted_at, is_deleted) FROM stdin;
nin	65d34fc0-c3b2-4786-8915-cf3f88c0ba94	12131313232	\N	pending	b9fe939d-e035-4fd3-bd6c-315f5ba7878a	2025-11-14 21:23:00.101587+00	2025-11-14 21:23:00.101587+00	\N	f
nin	a86d5d34-0f9e-4f7f-a213-64799896c15b	12131313232	\N	pending	1035fe71-1917-429a-b689-3f02af6186b0	2025-11-21 20:55:24.762646+00	2025-11-21 20:55:24.762646+00	\N	f
nin	8f4ef08b-7092-440c-9d03-d5b06101b03a	12345678909	\N	pending	d3430c2b-17a5-4ffe-86ce-224d6d23a6cf	2025-11-26 13:17:16.998612+00	2025-11-26 13:17:16.998612+00	\N	f
nin	9038937c-ce22-41ea-9219-8d4f3e2b6797	62603630556	\N	pending	a8062ce4-a838-4f90-9745-c1f829d3486b	2026-03-05 00:45:28.530597+00	2026-03-05 00:45:28.530597+00	\N	f
nin	132c3485-4922-4c81-855f-f0032e42cb2d	37667366280	\N	pending	4e2a9cd4-a503-4119-a7fd-30d6af7b121c	2026-03-06 21:20:45.578209+00	2026-03-06 21:20:45.578209+00	\N	f
nin	d58ab67e-2125-4590-bf3a-dca699db87e9	12345644556	\N	pending	41708a9e-749d-4e33-83ab-bd5511b486aa	2026-03-11 13:50:07.282231+00	2026-03-11 13:50:07.282231+00	\N	f
\.


--
-- Data for Name: waitlists; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.waitlists (email, full_name, phone_number, institution, id, created_at, updated_at, deleted_at, is_deleted) FROM stdin;
afolabimubarak18@gmail.com	Mubarak Afolabi	08106244890	Olabisi Onabanjo University	452db27f-fb88-49a4-bcee-8dc9a94086dd	2025-11-14 20:46:53.833155+00	2025-11-14 20:46:53.833155+00	\N	f
techwithkhalid247@gmail.com	Japheth Khalid	08159461285	Olabisi Onabanjo University, Ago Iwoye	a57282d7-5eb4-4c78-b615-087c4528ef0b	2025-11-15 13:51:44.598592+00	2025-11-15 13:51:44.598592+00	\N	f
gavmildtess@gmail.com	Tom-Ekeuwei Success Teknade 	08169764319	Madonna University	eceba662-0701-4a60-b444-1d698e71235d	2025-11-16 18:20:52.234503+00	2025-11-16 18:20:52.234503+00	\N	f
japhijader@gmail.com	Jay	403215718477	Harvard University	ea86b2db-3ee0-48f9-b103-87e604c6eb13	2025-11-16 20:31:05.744647+00	2025-11-16 20:31:05.744647+00	\N	f
jessyoma001@gmail.com	Odiwonma Jessica oluomachi 	07017755923	Federal University, Ndifu-Alike	3fa868f8-980e-4461-97d8-baecaec09a9e	2025-11-16 20:47:06.946805+00	2025-11-16 20:47:06.946805+00	\N	f
okoyechidera2005@gmail.com	Okoye Anita Chidera	09164881232	Afe Babalola University, Ado-Ekiti	783656f4-6375-4208-a1e0-f77a1103e389	2025-11-16 21:27:23.501972+00	2025-11-16 21:27:23.501972+00	\N	f
hakuoro2794@gmail.com	Abdul-Wahab Yasmin Hakuoro	233543419790	University for Development Studies	3adf7f8d-e03a-40a2-bc94-e0fcb07bb1e5	2025-11-16 23:12:15.143981+00	2025-11-16 23:12:15.143981+00	\N	f
sommyz2006@gmail.com	Elvira	09070893234	University of Nigeria	faa14721-f77f-4591-9aa0-a86eebf6e790	2025-11-16 23:22:53.232744+00	2025-11-16 23:22:53.232744+00	\N	f
runogodwin32@gmail.com	Godwin Vanessa 	08130249763	National Open University of Nigeria, Lagos	c93bd1a1-7d3a-411d-b650-50c943e1dc23	2025-11-17 01:07:21.856935+00	2025-11-17 01:07:21.856935+00	\N	f
onabamijitofunmi@gmail.com	Onabamiji Jesutofunmi Ayomide 	07067066865	Obafemi Awolowo University,Ile-Ife	94bb070b-ea51-4ea0-bc39-5507e3620399	2025-11-17 04:27:16.812728+00	2025-11-17 04:27:16.812728+00	\N	f
sweetquilldreamss@gmail.com	Asher Harry	09020072327	National Open University of Nigeria, Lagos	54cdde84-85e3-4353-903a-d8302da13267	2025-11-17 08:34:55.859621+00	2025-11-17 08:34:55.859621+00	\N	f
dicksonhopeid@gmail.com	Dickson Hope	09124010419	Yaba College of Technology, Yaba	59ef44ca-2b0c-4cc5-b302-112036506961	2025-11-17 16:27:34.649515+00	2025-11-17 16:27:34.649515+00	\N	f
adwoaohene07@gmail.com	Samuella Ohene	233505428236	University of Ghana	b9c344c8-db71-428d-9cf4-49494812489e	2025-11-17 16:34:04.532973+00	2025-11-17 16:34:04.532973+00	\N	f
ayalogufavour67@gmail.com	Ayalogu Chukwufunanya Godsfavour	07044291402	Nnamdi Azikiwe University, Awka	5a7923c2-acbe-4290-834f-93ba9b17aada	2025-11-17 17:26:03.68713+00	2025-11-17 17:26:03.68713+00	\N	f
ajokeademodupeoluwa19@gmail.com	Abiodun omotoyosi 	08165054261	Federal University of Agriculture, Abeokuta	bf254329-9c36-49ae-b44f-784f611b9fcd	2025-11-17 21:08:10.923881+00	2025-11-17 21:08:10.923881+00	\N	f
blossompipeloluwa@gmail.com	Blossom 	09160951432	Achievers University, Owo	e3461846-e576-43ac-b55a-0921cc667ec2	2025-11-17 21:18:56.200389+00	2025-11-17 21:18:56.200389+00	\N	f
olumoyegunmercy@gmail.com	Mercy Mofesola Olumoyegun	12508793523	Thompson Rivers University	d689409d-1319-4b29-b870-e42459d513ad	2025-11-17 23:15:16.882295+00	2025-11-17 23:15:16.882295+00	\N	f
diobosuprince@gmail.com	Dio Prince	09068004786	Edwin Clark University, Kaigbodo	60c3441a-6cf7-469a-9771-13c21422d729	2025-11-18 06:17:36.815965+00	2025-11-18 06:17:36.815965+00	\N	f
johnbosconnamdi531@gmail.com	Johnbosco Nnamdi	08159089248	Nnamdi Azikiwe University, Awka	5c11aa87-52e1-4d7e-9c08-194d4b66c8b1	2025-11-18 13:09:22.310127+00	2025-11-18 13:09:22.310127+00	\N	f
nneomabianca3000@gmail.com	Nommy	08069267722	Nnamdi Azikiwe University, Awka	a4c878c4-f6e4-4448-a005-0ee96e18d177	2025-11-18 13:39:06.440957+00	2025-11-18 13:39:06.440957+00	\N	f
joshuaifeanyi256@gmail.com	Onugwu Joshua ifeanyichukwu 	08122321005	Nnamdi Azikiwe University, Awka	d9a67f70-cd1c-46e6-bf2f-d482a71daace	2025-11-18 13:53:48.284611+00	2025-11-18 13:53:48.284611+00	\N	f
evelynogbuefi700@gmail.com	Evelyn Ogbuefi	07053145061	Nnamdi Azikiwe University, Awka	dbd75dd1-c3bf-4b98-bea6-5732959513c1	2025-11-18 14:03:49.461692+00	2025-11-18 14:03:49.461692+00	\N	f
ninahenandez33@gmail.com	Young Gabby 	08106187552	Nnamdi Azikiwe University, Awka	92425bac-26d2-475f-8a64-85bcccc0171d	2025-11-18 14:18:13.313397+00	2025-11-18 14:18:13.313397+00	\N	f
njokuanastasia@1gmail.com	Anastasia	08084684490	Nnamdi Azikiwe University, Awka	5412aac7-5c39-45ef-bac1-8043b719df25	2025-11-18 14:44:06.002166+00	2025-11-18 14:44:06.002166+00	\N	f
ezemak74@gmail.com	Ezema kasiemobi promise 	08066138154	Nnamdi Azikiwe University, Awka	afeea6b8-9b89-48e2-ab06-7c454ee5a95f	2025-11-18 15:11:26.628127+00	2025-11-18 15:11:26.628127+00	\N	f
nwakilechimdindu67@gmail.com	Nwakile chimdindu meshach 	09015379880	Nnamdi Azikiwe University, Awka	721257b2-be21-43cc-ba85-5248dfe3463d	2025-11-18 15:31:03.912915+00	2025-11-18 15:31:03.912915+00	\N	f
franklyndoziem4god@gmail.com	Uregbu Franklyn Nnadozie 	08066458523	Nnamdi Azikiwe University, Awka	09205fab-c36f-4266-8b4a-b1bc0b569568	2025-11-18 15:31:41.672913+00	2025-11-18 15:31:41.672913+00	\N	f
sanisibeauty9@gmail.com	Sanusi beauty 	07040364248	Adekunle Ajasin University, Akungba	c2f6a4f9-209a-4ff9-8616-67bc030d8bab	2025-11-18 19:53:07.720608+00	2025-11-18 19:53:07.720608+00	\N	f
favouralaran@gmail.com	Alaran Favour Oladapo	07061193868	Osun State University	2010a52d-64b7-497d-b066-2937c8fad6f2	2025-11-19 01:06:31.305215+00	2025-11-19 01:06:31.305215+00	\N	f
zwelithinisimela@gmail.com	Zwelithini Simela	00263785116631	Jacobs University Bremen	e09dcbfa-7d88-44b3-b5e6-656fba731b74	2025-11-19 21:45:01.947182+00	2025-11-19 21:45:01.947182+00	\N	f
emekajoynazzy@gmail.com	Emeka-Nwafor Joy Chinaza 	07082404915	Nnamdi Azikiwe University, Awka	5fd46a84-d038-4db8-b3f6-57d7da7c2799	2025-11-20 10:42:19.501217+00	2025-11-20 10:42:19.501217+00	\N	f
danielezeike62@gmail.com	Chukwuebuka Ezeike	08107061072	University of Calabar	36eb6a03-d354-4011-8e9a-66e38b61edfe	2025-11-20 11:01:42.001841+00	2025-11-20 11:01:42.001841+00	\N	f
nworahebuka.a@gmail.com	Ebuka Augustus Nworah	09134846838	Nnamdi Azikiwe University, Awka	168dd20f-cf95-4c5b-92e1-e37c526abc3e	2025-11-20 11:40:01.480603+00	2025-11-20 11:40:01.480603+00	\N	f
Beulahnife@gmail.com	Beulah Nife	08165534393	Miva Open University	79c2ee19-a215-4907-bbee-764f6b7901fb	2025-11-21 19:46:04.187132+00	2025-11-21 19:46:04.187132+00	\N	f
joanchidiebere@gmail.com	Chidiebere Joan	07064996420	Nnamdi Azikiwe University, Awka	fba8c1e0-d1f6-4ed8-a734-bbdec043486c	2025-11-22 09:50:26.861444+00	2025-11-22 09:50:26.861444+00	\N	f
okwuorakingsley4@gmail.com	Okwuora Kingsley	08117480075	Nnamdi Azikiwe University, Awka	70cfc42c-f780-4e4c-8cfb-0da0ed3f885e	2025-11-29 09:47:01.179394+00	2025-11-29 09:47:01.179394+00	\N	f
estherokolie890@gmail.com	Okolie Esther Oluebubechuckwu 	09061515636	Nnamdi Azikiwe University, Awka	1dab9de5-0072-489c-98f9-5ef4991edf95	2025-11-29 09:57:44.374951+00	2025-11-29 09:57:44.374951+00	\N	f
ezehchristiansobechukwu@gmail.com	EZEH CHRISTIAN SOBECHUKWU 	2349131548818	Nnamdi Azikiwe University, Awka	e5865ef4-5bb2-4536-9cc1-3ab08c8b78c0	2025-11-29 09:58:13.557207+00	2025-11-29 09:58:13.557207+00	\N	f
anitachukwuma557@gmail.com	Anita Chukwuma	08137933282	Nnamdi Azikiwe University, Awka	b2b03865-f06a-4ac6-98ee-2c6d858c27a4	2025-11-29 10:08:20.056628+00	2025-11-29 10:08:20.056628+00	\N	f
nwachukwuchidera16@gmail.com	Nwachukwu Chidera Jennifer 	09138785677	Nnamdi Azikiwe University, Awka	a70621cb-93b9-45be-b417-23d7d41c60a2	2025-11-29 10:10:18.880829+00	2025-11-29 10:10:18.880829+00	\N	f
bertykac@gmail.com	Eloilo Bertilla Ifeadikachi 	09162036036	Nnamdi Azikiwe University, Awka	52f9df9e-6cd2-47ed-acda-2a9e35f1e7a8	2025-11-29 10:19:00.263781+00	2025-11-29 10:19:00.263781+00	\N	f
franciscochukwuma35@gmail.com	Unachu Chukwuma Joshua 	07040394507	Nnamdi Azikiwe University, Awka	8f885506-5525-4366-a4e0-0a5225b40036	2025-11-29 10:35:56.112125+00	2025-11-29 10:35:56.112125+00	\N	f
snetgreat@gmail.com	Nwana great ikechukwu 	08137848519	University of Port-Harcourt	0c5f3d02-51b8-4c78-9e0e-049e79544b1c	2025-11-29 10:36:15.810862+00	2025-11-29 10:36:15.810862+00	\N	f
ikevictorychisom@gmail.com	Victory Ike	09070854530	Nnamdi Azikiwe University, Awka	c8d674a6-faad-49fb-8a5d-ff842bb26b71	2025-11-29 10:43:57.199892+00	2025-11-29 10:43:57.199892+00	\N	f
juliaopara7@gmail.com	Opara Julia	08038479058	Nnamdi Azikiwe University, Awka	a2d34e8c-ab57-428e-9715-6c23c2ab09db	2025-11-29 10:46:06.493107+00	2025-11-29 10:46:06.493107+00	\N	f
peacechielotamokafor@gmail.com	Peace Chielotam Okafor 	08162355924	Nnamdi Azikiwe University, Awka	2a029fa9-2fa3-40f0-b346-8b36fbbe7b97	2025-11-29 10:48:07.052675+00	2025-11-29 10:48:07.052675+00	\N	f
ehiruth61@gmail.com	Ruth Okewu	08106933780	Howard University	8168d446-b9e2-4687-bf77-59d572265405	2025-11-29 11:03:07.185321+00	2025-11-29 11:03:07.185321+00	\N	f
austinoibegbu@gmail.com	Augustine Ibegbu	09067558509	Nnamdi Azikiwe University, Awka	72aebe2e-74c0-44ee-aff6-f346109ed8da	2025-11-29 11:14:10.076421+00	2025-11-29 11:14:10.076421+00	\N	f
chineduokaforkenechukwu@gmail.com	Kenechukwu Kingsley Chinedu-Okafor 	2348104433928	Nnamdi Azikiwe University, Awka	60870221-a01e-4c08-a826-864da5078f9f	2025-11-29 11:15:37.728605+00	2025-11-29 11:15:37.728605+00	\N	f
oyeleyedavid001@gmail.com	Oyeleye David Temitope	09135958374	University of Ibadan	506077e1-9699-42c7-875a-08f3e1185f91	2025-11-29 12:02:39.81238+00	2025-11-29 12:02:39.81238+00	\N	f
olayinkahajarat922@gmail.com	Lawal olayinka hajarat 	07041548641	Ladoke Akintola University of Technology, Ogbomoso	ba91085b-b6c4-4e4e-9e9c-8301020a384d	2025-11-29 12:38:25.836203+00	2025-11-29 12:38:25.836203+00	\N	f
rahmatakande4@gmail.com	Rahmat Akande	08082255894	Ladoke Akintola University of Technology, Ogbomoso	6b3422d2-d423-4647-a129-f123eff13f5e	2025-11-29 13:07:55.243122+00	2025-11-29 13:07:55.243122+00	\N	f
rajiolalekanh247@gmail.com	Raji Olalekan	07045236428	University of Ibadan	5e9a1a71-5300-4a77-af12-05659f710dd2	2025-11-29 13:40:34.78885+00	2025-11-29 13:40:34.78885+00	\N	f
alamugloria21@gmail.com	Alamu Gloria 	09155097003	Ladoke Akintola University of Technology, Ogbomoso	30c1d975-bab6-4818-a297-81e51a385987	2025-11-29 14:18:53.169328+00	2025-11-29 14:18:53.169328+00	\N	f
olasojinifemi67@gmail.com	Olasoji Oluwanifemi Loveth	08054682103	Ondo State University of Science and Technology Okitipupa	fa384059-9aab-443f-9426-6ba0565b4794	2025-11-29 14:42:37.432974+00	2025-11-29 14:42:37.432974+00	\N	f
tonyettech@gmail.com	Anthony Oyenuga	07034345702	University of Ibadan	500e2504-e9a6-40ba-bffa-d7a4fb44ea5d	2025-11-29 14:57:11.188542+00	2025-11-29 14:57:11.188542+00	\N	f
peculiarlove20@gmail.com	Adegoke Oyindamola	09162558324	University of Ibadan	c5ebd199-1645-4ee6-a0ea-dbfaa428f3d6	2025-11-29 15:44:27.010058+00	2025-11-29 15:44:27.010058+00	\N	f
franciscaadenuga@gmail.com	Adenuga Francisca Oluwatosin 	08029664579	Olabisi Onabanjo University, Ago Iwoye	766d13c1-5489-497c-9c32-793af83d5583	2025-12-02 09:51:14.080258+00	2025-12-02 09:51:14.080258+00	\N	f
oluyoleboluwatife055@gmail.com	Oluyole Boluwatife 	09126740099	Olabisi Onabanjo University, Ago Iwoye	faf5f911-f0dd-4ed1-970b-0ffd1ded9aca	2025-12-02 12:44:08.929544+00	2025-12-02 12:44:08.929544+00	\N	f
robiatabeke949@gmail.com	Aremu Robiat Abeke 	08106906760	Olabisi Onabanjo University, Ago Iwoye	c1bb4f9e-42f7-4eb5-aa96-719525e8bcb2	2025-12-02 13:42:22.415534+00	2025-12-02 13:42:22.415534+00	\N	f
ramadan41999@gmail.com	Ramadan kazeem	09164114491	Olabisi Onabanjo University, Ago Iwoye	64a8b1bd-3ea5-4114-9a93-c436b82bb9e8	2025-12-02 13:53:20.515207+00	2025-12-02 13:53:20.515207+00	\N	f
subomiisrael@gmail.com	James Ayosubomi	07048151620	Olabisi Onabanjo University, Ago Iwoye	be8b8e65-a6ff-4b5d-b793-8988b10fc66a	2025-12-02 14:03:50.486671+00	2025-12-02 14:03:50.486671+00	\N	f
ademolaolayinka16@gmail.com	Habeeb Egberongbe	09045440496	Olabisi Onabanjo University, Ago Iwoye	6dd79410-fc84-4036-b245-667a6638cb7e	2025-12-02 23:02:45.980195+00	2025-12-02 23:02:45.980195+00	\N	f
adegboyegamuhammed20@gmail.com	Adegboyega Muhammed	09020756782	Olabisi Onabanjo University, Ago Iwoye	3be08a96-ce93-4328-aa45-6c444eb0993a	2025-12-03 05:55:14.388382+00	2025-12-03 05:55:14.388382+00	\N	f
ibrahimadegbenga39@gmail.com	Amisu Ibrahim Adegbenga 	09071734033	Olabisi Onabanjo University, Ago Iwoye	ce1d54aa-10b8-4132-89d9-e7610914851e	2025-12-03 06:04:55.066261+00	2025-12-03 06:04:55.066261+00	\N	f
maheersanee0@gmail.com	Mukhtar Sani Shehu	09049946418	Ahmadu Bello University, Zaria	94eecf74-9fa9-4f8a-bb46-53505d478f3c	2025-12-03 06:06:22.585298+00	2025-12-03 06:06:22.585298+00	\N	f
kamolideenibikunle@gmail.com	Ibikunle kamolideen olanrewaju 	08083476163	University of Ilorin	ae53c153-1678-45f0-9a92-f35325b649c3	2025-12-03 06:12:58.111932+00	2025-12-03 06:12:58.111932+00	\N	f
julusm55@gmail.com	Hassan musa	07032617164	University of Abuja, Gwagwalada	5ee7e5fc-643c-4a14-82dc-2afd2d040f4b	2025-12-03 06:15:55.0228+00	2025-12-03 06:15:55.0228+00	\N	f
elermeenmoh@gmail.com	Alamin Muhammad	08168253678	Al-Qalam University, Katsina	cb37632b-6b89-4a53-bb6a-850c16aeeb7d	2025-12-03 06:16:48.231441+00	2025-12-03 06:16:48.231441+00	\N	f
habeebolatunji383@gmail.com	Olatunji Habeeb	09035804757	Federal University of Technology, Minna	7765b18f-bb8b-4108-b2d4-04946ad2324d	2025-12-03 06:20:54.433712+00	2025-12-03 06:20:54.433712+00	\N	f
adesinaabdmatin@gmail.com	Adesina Abdmatin Olamilekan	08142164048	Federal University of Technology, Minna	eae38f27-7e1b-4ba0-83f3-9b2bc6a440eb	2025-12-03 06:36:17.495028+00	2025-12-03 06:36:17.495028+00	\N	f
ayomideuthman876@gmail.com	Jimoh uthman ayomide 	07026764691	Bayero University, Kano	dd370530-3317-4e1a-9f98-3154671987bb	2025-12-03 10:00:35.232949+00	2025-12-03 10:00:35.232949+00	\N	f
akinladeadejoke926@gmail.com	Adejoke Bukola Akinlade	09056207684	Olabisi Onabanjo University, Ago Iwoye	76ea3abb-0c4a-4e62-85c7-796ef7a9a93f	2025-12-03 18:08:49.165565+00	2025-12-03 18:08:49.165565+00	\N	f
abdulhaqqjimoh@gmail.com	Jimoh Abdulhaqq	08108114742	Federal University of Agriculture, Abeokuta	0ea0d7e8-87a3-45b5-9c5b-85cd0fab72c3	2025-12-06 19:51:57.288702+00	2025-12-06 19:51:57.288702+00	\N	f
gloria73399@gmail.com	Akinyefa Oluwatosin Gloria	08160874177	University of Ilorin	5afac914-ef7d-42ad-b491-25a9f77e9bc6	2025-12-06 22:30:20.139609+00	2025-12-06 22:30:20.139609+00	\N	f
obasichidiebube99@gmail.com	Obasi Chidiebube	09150810342	Nnamdi Azikiwe University, Awka	50cf1840-2510-4b07-be60-2a2ec71d2b23	2025-12-07 15:19:19.506214+00	2025-12-07 15:19:19.506214+00	\N	f
shalomadebayo95@gmail.com	Shalom Ayoade 	08062883607	Olabisi Onabanjo University, Ago Iwoye	dec754c7-7f28-4b7f-95c0-fd17d60b47fa	2025-12-07 16:27:46.05807+00	2025-12-07 16:27:46.05807+00	\N	f
bolajitoluwalase@gmail.com	Jagun Dhikrullah	09034146925	Olabisi Onabanjo University, Ago Iwoye	0ad9ecb2-234c-40ac-b775-db3f7b422162	2025-12-08 07:52:24.555231+00	2025-12-08 07:52:24.555231+00	\N	f
chiamakafavour319@gmail.com	Iloduba Chiamaka 	08057343910	Nnamdi Azikiwe University, Awka	a00f75e8-da0f-41fd-9080-3280633b53f5	2025-12-08 09:31:46.656342+00	2025-12-08 09:31:46.656342+00	\N	f
ilodubachiamaka619@gmail.com	Iloduba Chiamaka	09026563340	Nnamdi Azikiwe University, Awka	34b49651-18f5-41e3-88c6-b315a3a56a3b	2025-12-08 09:35:11.656453+00	2025-12-08 09:35:11.656453+00	\N	f
alliayomide050@gmail.com	Ayomide Alli	08127966553	The Polytechnic, Ibadan	a2f24ebc-19fc-4bc8-b1bf-8b3fa6d981bf	2025-12-10 18:23:54.445672+00	2025-12-10 18:23:54.445672+00	\N	f
omotoyosiagboola74@gmail.com	Oyindamola Deji-Agboola	08154744802	Olabisi Onabanjo University, Ago Iwoye	3aca6173-4a5f-4d65-b1bd-a1cc239c9898	2025-12-10 19:43:55.789434+00	2025-12-10 19:43:55.789434+00	\N	f
oladeposhola33@gmail.com	Oladepo Shola	08083876891	Olabisi Onabanjo University, Ago Iwoye	a6186f7f-3de8-44a8-af9d-da5ddb2be50c	2025-12-11 04:15:28.112818+00	2025-12-11 04:15:28.112818+00	\N	f
abdulhakeemwaliyah623@gmail.com	Abdulhakeem Abidemi	09058389089	University of Ibadan	a2d4ca54-5e5d-4039-9d04-6241266030cb	2025-12-12 20:35:33.377107+00	2025-12-12 20:35:33.377107+00	\N	f
aladevictortimothy@gmail.com	Alade Victor 	07040794313	University of Ibadan	70490761-4f4c-4b58-8801-27f6d89f4b02	2025-12-12 20:41:30.913306+00	2025-12-12 20:41:30.913306+00	\N	f
ayomidemorenikeji040@gmail.com	Mubarak Abdulkareem	07040956574	Fountain Unveristy, Oshogbo	45734fbe-3bc7-4e54-9d8c-f957e81e808e	2025-12-12 20:41:41.659756+00	2025-12-12 20:41:41.659756+00	\N	f
lilianayanwu2001@gmail.com	Ngozi Anyanwu	2348143441524	National Open University of Nigeria, Lagos	38033c9e-7fb1-4d87-8a30-41e5f713b645	2025-12-13 01:03:18.730529+00	2025-12-13 01:03:18.730529+00	\N	f
agbaraoluwasimiloluwa@gmail.com	Aderemi Agbaraoluwa	07012582514	Federal University of Technology, Minna	e727e413-6527-400d-9e60-4c57947d409e	2025-12-13 04:42:03.437625+00	2025-12-13 04:42:03.437625+00	\N	f
vukecha@gmail.com	Ukecha victor	09057126335	The Polytechnic, Ibadan	7c033da1-e7b0-434e-b411-7296811b549a	2025-12-13 20:44:00.173592+00	2025-12-13 20:44:00.173592+00	\N	f
usalmah224@gmail.com	Umar Selimat Oluwatunmishe 	2347014666564	Lagos State University, Ojo	0876c2fc-bc99-4e5f-83b3-f95c6802245f	2025-12-14 18:02:13.121248+00	2025-12-14 18:02:13.121248+00	\N	f
adeyosola11@gmail.com	Abdullah Adeyosola Abubakr	09034047944	Olabisi Onabanjo University, Ago Iwoye	0a059ed7-672d-4d03-ae82-4678d2233447	2025-12-15 05:21:51.325485+00	2025-12-15 05:21:51.325485+00	\N	f
davidolafare94@gmail.com	Olafare Oluwadamilare David 	2348162415018	Olabisi Onabanjo University, Ago Iwoye	79277a64-b642-4ee7-8e53-46bed727fab3	2025-12-15 05:24:22.095285+00	2025-12-15 05:24:22.095285+00	\N	f
favoursofoluwe5@gmail.com	Sofoluwe Favour Moyinoluwa 	08071373871	Olabisi Onabanjo University, Ago Iwoye	8384dda1-1d3f-4d73-ae44-47707924e3bd	2025-12-16 15:55:59.035827+00	2025-12-16 15:55:59.035827+00	\N	f
ogbuaguifeanyi236@gmail.com	Ogbuagu IFEANYI Desmond 	07072316055	Federal University of Technology, Owerri	1fd303c0-db04-4a05-bc6d-b2905c1e2864	2025-12-17 15:33:32.985421+00	2025-12-17 15:33:32.985421+00	\N	f
ajeyimary4@gmail.com	Ajeyi  Mary 	2349064262361	Benue State University, Makurdi	0ca84aba-5929-4f18-bf0e-2c88667ace48	2025-12-17 22:53:58.675435+00	2025-12-17 22:53:58.675435+00	\N	f
holdmetight0100@gmail.com	Muhammad Sani Abdullahi 	09011862453	Federal University of Technology, Minna	9c638cdf-826b-4ab2-b848-1290e6917245	2025-12-18 21:34:29.0211+00	2025-12-18 21:34:29.0211+00	\N	f
okekelilian82007@gmail.com	Okeke Lilian Chisom 	08122699234	Enugu State University of Science and Technology, Enugu	740c8b19-f66b-4b63-87aa-4396cc1d6133	2025-12-19 22:51:35.892044+00	2025-12-19 22:51:35.892044+00	\N	f
ifeoluwaafolabi86@gmail.com	Ifeoluwa 	08070585505	Afe Babalola University, Ado-Ekiti	93f339e8-bcb7-4f50-aac0-b87cf82ffca0	2025-12-20 00:33:08.960083+00	2025-12-20 00:33:08.960083+00	\N	f
styledby1505@gmail.com	Abiodun Fathia Ayomide 	07085812883	Olabisi Onabanjo University, Ago Iwoye	7f6f5308-1ade-4926-a973-b9083118fb9f	2025-12-21 20:37:33.493629+00	2025-12-21 20:37:33.493629+00	\N	f
aolawumi442@gmail.com	OLAWUMI AISHAT ABIDEMI	09122425847	Ladoke Akintola University of Technology, Ogbomoso	c923a3d9-3de8-40da-872e-4af66e218e3e	2025-12-22 04:36:02.354022+00	2025-12-22 04:36:02.354022+00	\N	f
johnolaoluwaekundayo@gmail.com	Ekundayo John 	08162782636	Federal University of Technology, Akure	c0b6fdba-70a8-4204-96d9-2eabde3c688c	2025-12-24 19:22:25.887551+00	2025-12-24 19:22:25.887551+00	\N	f
halimatamzat001@gmail.com	Amzat Halimat Omowunmi 	08101811538	University of Lagos	c8f02285-c53b-4a01-aa49-21a36d3a216b	2025-12-28 09:00:10.152595+00	2025-12-28 09:00:10.152595+00	\N	f
stommy133@hotmail.com	Victorious Victor	08152161484	Olabisi Onabanjo University, Ago Iwoye	8e0c2da9-48cd-4e26-8ae9-fda3cf8eff9b	2026-01-09 20:28:48.61874+00	2026-01-09 20:28:48.61874+00	\N	f
Ajayihabeeb997@gmail.com	Habeeb Ajayi	09036977142	Olabisi Onabanjo University, Ago Iwoye	15adf02a-21ad-458b-999d-486cfcb28f59	2026-01-09 21:53:50.346971+00	2026-01-09 21:53:50.346971+00	\N	f
salaudeenabdulazeez077@gmail.com	Salaudeen Abdulazeez	08024768339	Olabisi Onabanjo University	e551107d-3f7e-43d8-ad14-38111f3ef0f9	2026-01-11 20:52:01.45575+00	2026-01-11 20:52:01.45575+00	\N	f
mosesobayomi2@gmail.com	OBAYOMI MOSES BOLUWATIFE 	09025678625	Olabisi Onabanjo University, Ago Iwoye	2e2cb22e-ca9c-4e5b-a620-d25f39152201	2026-01-13 10:51:20.188233+00	2026-01-13 10:51:20.188233+00	\N	f
abiolaolamilekan797@gmail.com	Abiola Olamilekan	09041156313	Olabisi Onabanjo University, Ago Iwoye	1b78b701-0215-4a23-bf11-b384e5986bce	2026-01-13 10:53:58.400724+00	2026-01-13 10:53:58.400724+00	\N	f
odukoyafemi5@gmail.com	Odukoya Olabode Oluwafemi 	08050235818	Olabisi Onabanjo University, Ago Iwoye	507db4a4-cfa2-472d-b4b9-f0db3f747fc0	2026-01-13 10:55:48.935538+00	2026-01-13 10:55:48.935538+00	\N	f
samueloluwafemi162@gmail.com	Olayeye Samuel 	07026000226	Olabisi Onabanjo University, Ago Iwoye	249a57f1-edf3-4719-bb5c-fef3d8d2a46d	2026-01-13 11:08:04.496779+00	2026-01-13 11:08:04.496779+00	\N	f
olugbengadaniel130@gmail.com	Olugbenga Daniel	08157927623	Olabisi Onabanjo University, Ago Iwoye	c3934ec5-96bc-4629-bddf-856aadac37f0	2026-01-13 15:19:43.132185+00	2026-01-13 15:19:43.132185+00	\N	f
mayorfox9@gmail.com	Okeshola Desmond	07039165368	Olabisi Onabanjo University, Ago Iwoye	2bf1df44-bab4-4a5d-a018-939660500e59	2026-01-13 15:28:03.995334+00	2026-01-13 15:28:03.995334+00	\N	f
davidbabatunde484@gmail.com	Babatunde David Itunuoluwa	07016458993	Olabisi Onabanjo University, Ago Iwoye	51491739-8c64-4183-98f9-802eb4328f60	2026-01-13 15:36:37.662457+00	2026-01-13 15:36:37.662457+00	\N	f
emmanueldekunle0@gmail.com	Alao 	08064698403	Olabisi Onabanjo University, Ago Iwoye	bb70b48d-a0bb-45a6-a8f2-12529ef651ba	2026-01-13 15:38:21.159683+00	2026-01-13 15:38:21.159683+00	\N	f
osundairoazeezat@gmail.com	Azeezat Osundairo	09048916658	Olabisi Onabanjo University, Ago Iwoye	95f2a72f-1938-481e-a705-b7a6542fb40f	2026-01-14 12:57:18.740018+00	2026-01-14 12:57:18.740018+00	\N	f
olunusimiracle@gmail.com	Olunusi Miracle Obaloluwa 	08134674447	Olabisi Onabanjo University, Ago Iwoye	44c43ddb-0b60-47d2-8ce3-578070a1a2b5	2026-01-14 13:25:55.582425+00	2026-01-14 13:25:55.582425+00	\N	f
ojuolapelawal9@gmail.com	Lawal Temitayo 	08167888832	Olabisi Onabanjo University, Ago Iwoye	13d45611-f4ef-4a49-bbb2-769adb2d05f4	2026-01-14 13:38:29.999176+00	2026-01-14 13:38:29.999176+00	\N	f
oluwaferanmidaniel15@gmail.com	Oluwaferanmi Daniel	09158543066	Olabisi Onabanjo University, Ago Iwoye	8d654739-8eda-4ea9-9185-eaba9bdcaf41	2026-01-14 14:01:45.704824+00	2026-01-14 14:01:45.704824+00	\N	f
essajoe001@gmail.com	Esther Joseph 	09151874719	Olabisi Onabanjo University, Ago Iwoye	4589b04f-c38a-4975-a479-8c85699a6933	2026-01-14 18:54:00.207741+00	2026-01-14 18:54:00.207741+00	\N	f
hikmateniola912@gmail.com	Eniola 	07066362375	Olabisi Onabanjo University, Ago Iwoye	076852d0-d6b3-4a54-80a5-92e7822829a2	2026-01-14 18:55:50.169097+00	2026-01-14 18:55:50.169097+00	\N	f
ikeanyichidera400@gmail.com	Ikeanyi Chidera	07050340391	Olabisi Onabanjo University	a0133a55-8336-40e3-b6f1-50aa4031e7a9	2026-01-14 19:17:13.314277+00	2026-01-14 19:17:13.314277+00	\N	f
osariemensuccessomere@gmail.com	Omere success osariemen	09050287633	Olabisi Onabanjo University, Ago Iwoye	1a32ae96-a9b0-48d6-ba70-4568c131442a	2026-01-14 19:24:13.72763+00	2026-01-14 19:24:13.72763+00	\N	f
isnailtaiwo85@gmail.com	Ismail taiwo	08164238608	Olabisi Onabanjo University	50bb2fe9-4122-4d46-a1b1-3534324715df	2026-01-14 19:25:49.213625+00	2026-01-14 19:25:49.213625+00	\N	f
jlucifer149@gmail.com	Samuel 	07059471598	Olabisi Onabanjo University, Ago Iwoye	b5bd3219-3649-47d3-8e7a-b4fdfcd3f155	2026-01-14 19:31:50.172261+00	2026-01-14 19:31:50.172261+00	\N	f
boyejooluwatosin19@gmail.com	Boyejo oluwatosin Ayomide	08123015611	Abdu Gusau Polytechnic, Talata-Mafara	25a8b128-f330-480e-b9a6-74ccb96f5b2e	2026-01-17 08:46:21.644581+00	2026-01-17 08:46:21.644581+00	\N	f
omolarasenami7@gmail.com	Amusa Omolara	09026896790	Olabisi Onabanjo University, Ago Iwoye	6075849e-bab5-4145-a6b6-e2a89e4569d1	2026-01-21 13:10:55.347236+00	2026-01-21 13:10:55.347236+00	\N	f
oreoluwaadefowora8@gmail.com	Adefowora Ganiyat Oreoluwa	07054733155	Olabisi Onabanjo University, Ago Iwoye	30a25188-6e30-416b-821f-54a2183a6228	2026-02-04 19:26:18.091436+00	2026-02-04 19:26:18.091436+00	\N	f
abbiebarbie67@gmail.com	Abigael Oluwafunmilayo 	07078781458	Olabisi Onabanjo University, Ago Iwoye	9a50112b-58e0-4a45-a051-b464d10f9ced	2026-02-04 20:09:21.087993+00	2026-02-04 20:09:21.087993+00	\N	f
favourpatrick131@gmail.com	Favour Patrick	08127313597	Chukwuemeka Odumegwu Ojukwu University, Uli	b7e4520c-aeec-4da9-b01a-af997abc2627	2026-02-06 07:42:22.165546+00	2026-02-06 07:42:22.165546+00	\N	f
chukwumapraise84@gmail.com	Praise Chukwuma	08067173592	Chukwuemeka Odumegwu Ojukwu University, Uli	9024c3e6-e009-4fbb-bca6-af147fc7da72	2026-02-06 07:42:23.791869+00	2026-02-06 07:42:23.791869+00	\N	f
michellechibunkem@gmail.com	Chibunkem Michelle	2349011792118	Chukwuemeka Odumegwu Ojukwu University, Uli	112153c5-10ca-4f7b-856a-11e83bf80922	2026-02-06 07:42:26.584305+00	2026-02-06 07:42:26.584305+00	\N	f
izuchukwuhenry@gmail.com	Nduakpo izuchukwu henry	07085086523	Chukwuemeka Odumegwu Ojukwu University, Uli	5741740c-2338-48ce-b6ef-9c10b2574d5b	2026-02-06 09:51:04.232088+00	2026-02-06 09:51:04.232088+00	\N	f
eniolabasira93@gmail.com	Jimoh Eniola Basira 	09042297441	Olabisi Onabanjo University, Ago Iwoye	52ce691b-d833-4430-aa84-23ab028a8144	2026-02-06 11:43:46.022973+00	2026-02-06 11:43:46.022973+00	\N	f
festusprecious45@gmail.com	festus precious	09124160687	Nnamdi Azikiwe University, Awka	34acd8a0-0030-4e05-a2a9-51f5b36e590b	2026-02-08 15:02:30.729799+00	2026-02-08 15:02:30.729799+00	\N	f
janefranceschioma248@gmail.com	Nwabuike chioma janefrances 	08146970865	Chukwuemeka Odumegwu Ojukwu University, Uli	4ba0cddb-fa16-46df-8883-4bc7432b1a5c	2026-02-19 08:25:19.826533+00	2026-02-19 08:25:19.826533+00	\N	f
oluebubemirabel515@gmail.com	Oluebube Mirabel	08146295991	Chukwuemeka Odumegwu Ojukwu University, Uli	839d3eab-84c5-494b-af38-d2323be4ae46	2026-02-19 09:32:30.638084+00	2026-02-19 09:32:30.638084+00	\N	f
chinemelemfavour@gmail.com	Favourite 	07035103498	Chukwuemeka Odumegwu Ojukwu University, Uli	bd69ee69-aa16-4def-a3f5-b5d063b6e240	2026-02-19 09:35:26.622484+00	2026-02-19 09:35:26.622484+00	\N	f
praisechikezie57@gmail.com	CHIKEZIE TOCHUKWU PRAISE 	09113568572	Chukwuemeka Odumegwu Ojukwu University, Uli	ef811498-95f0-4dda-8bdf-abdd1825d7cd	2026-02-19 10:21:31.209794+00	2026-02-19 10:21:31.209794+00	\N	f
mannyfrosh26@gmail.com	Nweke Francis chiemerie 	09160282567	Chukwuemeka Odumegwu Ojukwu University, Uli	d1e0c9d6-9180-436c-bef3-3da5870fa105	2026-02-19 11:08:19.811745+00	2026-02-19 11:08:19.811745+00	\N	f
mikaillawal87@gmail.com	Mika'il Muhammad lawal 	09037376628	Federal University of Technology, Minna	a5f04e3f-7d24-4a0e-bfa8-40bab7f1c7c6	2026-02-19 11:38:40.450206+00	2026-02-19 11:38:40.450206+00	\N	f
idehofaithential@gmail.com	Ideho faith Oghenerukevwe 	09078310514	Chukwuemeka Odumegwu Ojukwu University, Uli	cc05a47e-6508-4fe3-805a-04d6618b6089	2026-02-19 12:05:00.268296+00	2026-02-19 12:05:00.268296+00	\N	f
chukwuemekap9@gmail.com	Paul Ebuka Chukwuemeka	08144439340	Chukwuemeka Odumegwu Ojukwu University, Uli	92b00b5e-9ecd-4b88-afe8-d9e88ede20e0	2026-02-19 20:50:08.591503+00	2026-02-19 20:50:08.591503+00	\N	f
ebubechukwuarize@gmail.com	Arize	09061296800	Akwa Ibom State University of Technology, Uyo	f6528b79-b8de-45c7-b515-9d6339bebbf2	2026-02-19 20:58:43.305211+00	2026-02-19 20:58:43.305211+00	\N	f
scholasticaeze61@gmail.com	Ezejelue kosisochukwu scholastica 	09032575452	Chukwuemeka Odumegwu Ojukwu University, Uli	bbade3c3-36de-40b8-be45-2c6f4f3bf77f	2026-02-20 01:34:29.578186+00	2026-02-20 01:34:29.578186+00	\N	f
fahvourdice@gmail.com	Okonkwo favour amarachi 	08137425799	Chukwuemeka Odumegwu Ojukwu University, Uli	d23ce91c-07e8-46c4-a90f-d9d15adbf091	2026-02-20 07:42:10.402279+00	2026-02-20 07:42:10.402279+00	\N	f
umaryannchiamaka@gmail.com	Udoba Maryann Chiamaka 	08027693602	Chukwuemeka Odumegwu Ojukwu University, Uli	0751a7a4-b791-4c57-a3e8-66ff60586ee0	2026-02-20 09:03:47.705891+00	2026-02-20 09:03:47.705891+00	\N	f
ebubechukwujasper@gmail.com	Arize Ebubechukwu jasper	09061296800	Abia State College of Education (Technical), Arochukwu	b81013e2-6ab5-477e-8609-d2f0c18d7970	2026-02-19 21:00:09.165638+00	2026-02-19 21:00:09.165638+00	\N	f
stannwoti1@gmail.com	Stan Nwoti	07062402982	Nnamdi Azikiwe University, Awka	00e88e69-f716-40f4-845b-1cff782d5f7d	2026-02-20 16:07:53.927541+00	2026-02-20 16:07:53.927541+00	\N	f
Okekeonyinyechukwu55@gmail.com	Okeke onyinyechukwu Angela 	07073498981	Nnamdi Azikiwe University, Awka	e0f4666b-b3db-46bc-8bc6-d7bab5a77445	2026-02-20 21:58:58.809469+00	2026-02-20 21:58:58.809469+00	\N	f
okerekeemmanuel4000@gmail.com	Okereke Emmanuel Basil 	08123689153	Olabisi Onabanjo University, Ago Iwoye	44c4bca3-5c14-4b1e-9eec-2f47e15469de	2026-02-25 12:18:48.747804+00	2026-02-25 12:18:48.747804+00	\N	f
owunnae12@gmail.com	Owunna Emmanuel	09117595460	Chukwuemeka Odumegwu Ojukwu University, Uli	e076f62a-37ed-4408-b26f-908926e11842	2026-02-25 19:14:55.937099+00	2026-02-25 19:14:55.937099+00	\N	f
officialedward29@gmail.com	Olusola Somorin	09130411877	Olabisi Onabanjo University, Ago Iwoye	3076d849-1408-4710-acfa-684285ef38b9	2026-02-26 07:02:50.36385+00	2026-02-26 07:02:50.36385+00	\N	f
joyabioye884@gmail.com	Abioye Oluwadamilola Joy 	09160628950	Obafemi Awolowo University,Ile-Ife	5a758fbe-d3f3-4fb7-837e-474b0f145ae0	2026-02-26 07:05:19.016822+00	2026-02-26 07:05:19.016822+00	\N	f
iloridavid92@gmail.com	Ilori David 	09067469392	Olabisi Onabanjo University, Ago Iwoye	91c2d246-5ab6-4f0f-9637-1fe9db827647	2026-02-27 07:30:29.479351+00	2026-02-27 07:30:29.479351+00	\N	f
ikebudehgideon@gmail.con	Gideon	07088114692	Nnamdi Azikiwe University, Awka	18df71b7-b3fc-4cf3-af2d-e706a7fe71fe	2026-02-27 14:32:35.305018+00	2026-02-27 14:32:35.305018+00	\N	f
ajadii228@gmail.com	Oludare Ajadi	08128764690	Olabisi Onabanjo University, Ago Iwoye	1a8c857e-6f77-4bda-8298-3199f5d62f44	2026-03-03 18:23:25.429013+00	2026-03-03 18:23:25.429013+00	\N	f
damilolajanetatilola@gmail.com	Atilola Damilola Janet	09056707994	Federal University of Agriculture, Abeokuta	e60875ba-e844-42eb-bbe4-e40aa0710092	2026-03-04 12:32:25.648232+00	2026-03-04 12:32:25.648232+00	\N	f
pelumiajoke91@gmail.com	Abati pelumi adejoke 	08070601858	Federal University of Agriculture, Abeokuta	5e827545-969f-44c3-b77c-73974a408beb	2026-03-04 12:42:51.260108+00	2026-03-04 12:42:51.260108+00	\N	f
sogeyinbomistura@gmail.com	Sogeyinbo Mistura Abiodun 	08142317500	Federal University of Agriculture, Abeokuta	9ba6c7ea-d5cd-432b-9a0c-05c3f571ced5	2026-03-04 12:42:58.593885+00	2026-03-04 12:42:58.593885+00	\N	f
soyelejanet@gmail.com	Soyele Gbemisola	08106398034	Federal University of Agriculture, Abeokuta	c3793654-64da-481d-9821-24aade562336	2026-03-04 12:43:35.46973+00	2026-03-04 12:43:35.46973+00	\N	f
etzrarediamond02@gmail.com	Adeniji Darasimi 	08128706210	Federal University of Agriculture, Abeokuta	b7d93788-6482-49ba-9c28-e5ead5c42ddc	2026-03-04 12:45:52.711922+00	2026-03-04 12:45:52.711922+00	\N	f
lawalayodeji57.ta@gmail.com	Jap	2349131841928	Olabisi Onabanjo University, Ago Iwoye	c92296be-0d9b-4e60-b1fd-24ffcc448195	2026-03-05 00:59:08.152625+00	2026-03-05 00:59:08.152625+00	\N	f
lakpastephanie0@gmail.com	Lakpa Stephanie	08139654245	Afe Babalola University, Ado-Ekiti	db7a0c61-6136-4c4f-a3a6-5093ec0e1302	2026-03-08 09:32:59.88691+00	2026-03-08 09:32:59.88691+00	\N	f
ayomideadekoya138@gmail.com	Adekoya Ayomide Hannah	08149757797	Olabisi Onabanjo University, Ago Iwoye	ccd6794c-0f1a-4614-ac95-03425859cdc8	2026-03-10 12:19:44.764067+00	2026-03-10 12:19:44.764067+00	\N	f
ifeanyinduba7@gmail.com	Ifeanyi James Nduba 	08125471543	Nnamdi Azikiwe University, Awka	5cf4f925-c0f9-4f1a-88da-07f592dcbdda	2026-03-11 11:10:02.512201+00	2026-03-11 11:10:02.512201+00	\N	f
estheriyanoye26@gmail.com	Iyanoye Esther	08145431104	Olabisi Onabanjo University, Ago Iwoye	d96a2e54-bb36-45b6-9e75-038b080aaab9	2026-03-11 12:15:18.653597+00	2026-03-11 12:15:18.653597+00	\N	f
evangmayowa@gmail.com	Ajala Mayowa henry	08066004896	Olabisi Onabanjo University, Ago Iwoye	243c35ab-eca8-42cb-af13-39e8eba8259a	2026-03-11 12:34:04.984847+00	2026-03-11 12:34:04.984847+00	\N	f
akinyemip366@gmail.com	Akinyemi precious 	07056937150	Olabisi Onabanjo University, Ago Iwoye	cc4201d8-6afb-4b70-b637-658360734a44	2026-03-12 13:13:03.72739+00	2026-03-12 13:13:03.72739+00	\N	f
laogunemmanuel1@gmail.com	Emmanuel Laogun	07042859075	Olabisi Onabanjo University, Ago Iwoye	4b7d3382-6cad-4e14-80eb-74cc58ddf77c	2026-03-12 14:39:00.915785+00	2026-03-12 14:39:00.915785+00	\N	f
adenariwooluwaseyi1@gmail.com	Oluwaseyi Adenariwo	08119653550	Olabisi Onabanjo University, Ago Iwoye	b0d29a01-8693-472a-befd-faa70a8d78a5	2026-03-12 15:26:16.225093+00	2026-03-12 15:26:16.225093+00	\N	f
adeitanmercy5@gmail.com	Adeitan Mercy Otelaja	09058364085	Olabisi Onabanjo University, Ago Iwoye	e13e0db0-c761-485a-b8e2-52f8bfd34cf2	2026-03-12 15:28:05.042256+00	2026-03-12 15:28:05.042256+00	\N	f
Timileyiniyanuoluwa743@gmail.com	Ibikunle timileyin iyanuoluwa 	08124372270	Olabisi Onabanjo University, Ago Iwoye	b9303a99-6d79-4e3c-829a-e2e97e3cfedb	2026-03-12 16:32:18.995824+00	2026-03-12 16:32:18.995824+00	\N	f
wisdomferanmi2@gmail.com	Ajbrainiac 	09076236188	Federal University of Technology, Akure	e80f0142-5d30-42a5-9326-73dc6026e26c	2026-03-14 21:38:41.076709+00	2026-03-14 21:38:41.076709+00	\N	f
\.


--
-- Data for Name: wallets; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.wallets (store_id, available_balance, pending_balance, withdrawable_balance, id, created_at, updated_at, deleted_at, is_deleted) FROM stdin;
655e5f63-e7d2-4f58-a677-f92ce108b08e	0	0	0	e7cfe792-2c7a-4114-8ee9-e31b76e1c4c2	2025-11-14 21:22:30.458263+00	2025-11-14 21:22:30.458263+00	\N	f
54a46d8d-a0e2-4610-a3ca-e1dab5c482ec	0	0	0	d251a1df-e35e-4f56-81a0-914e47e847cc	2025-11-21 20:52:15.421671+00	2025-11-21 20:52:15.421671+00	\N	f
c0f2f49a-c5c8-4b0e-ac8f-ccbfed153e06	0	0	0	b2d5332c-39bc-4b4c-bbe2-8ab9344c85c3	2025-11-24 17:28:43.851319+00	2025-11-24 17:28:43.851319+00	\N	f
40017d0f-2c8e-43cb-bccf-c79e3952e140	0	0	0	dbe8fac8-e0a8-435f-ac91-0acf6ef4eced	2025-11-26 13:16:38.00465+00	2025-11-26 13:16:38.00465+00	\N	f
cefc58e4-a720-40e2-9fe5-ff3efd650252	0	0	0	cb5d874b-2233-4c91-90ed-5988fcfe776b	2025-12-10 02:05:46.694358+00	2025-12-10 02:05:46.694358+00	\N	f
8115d9bf-ff36-4762-8bbf-e87c20a4d31a	0	0	0	3529790e-88d2-4ad4-8bdb-82e6c5620d76	2026-03-05 00:43:55.518491+00	2026-03-05 00:43:55.518491+00	\N	f
57224a25-f30f-4c74-9d7a-5686cdb8ebea	0	0	0	77c50cea-f34f-467a-b17a-245cf00616bf	2026-03-06 21:19:18.069296+00	2026-03-06 21:19:18.069296+00	\N	f
66cd00e1-1832-4e31-9dd7-179b9caa35ed	0	0	0	c3346074-2d53-4899-971f-9bc67463db40	2026-03-11 13:49:45.030835+00	2026-03-11 13:49:45.030835+00	\N	f
\.


--
-- Data for Name: wallet_transactions; Type: TABLE DATA; Schema: public; Owner: prisma_migration
--

COPY public.wallet_transactions (wallet_id, amount, transaction_type, status, id, created_at, updated_at, deleted_at, is_deleted) FROM stdin;
\.


--
-- PostgreSQL database dump complete
--

\unrestrict JP5541TJw27JIj9MCerJEsMB2h6iq7t0az1iMJKSlTc3DvWfup34DaRYWcg7yl9

