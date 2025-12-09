--
-- PostgreSQL database dump
--

\restrict HhkzwHC7CdF8GSen8AyBZyjxUpNgjMP0paQbt1fGRO3s5qRZsxPaNTIJg3OLUeJ

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: waitlists; Type: TABLE; Schema: public; Owner: prisma_migration
--

CREATE TABLE public.waitlists (
    email character varying NOT NULL,
    full_name character varying NOT NULL,
    phone_number character varying NOT NULL,
    institution character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    is_deleted boolean NOT NULL
);


ALTER TABLE public.waitlists OWNER TO prisma_migration;

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
\.


--
-- Name: waitlists waitlists_email_key; Type: CONSTRAINT; Schema: public; Owner: prisma_migration
--

ALTER TABLE ONLY public.waitlists
    ADD CONSTRAINT waitlists_email_key UNIQUE (email);


--
-- Name: waitlists waitlists_pkey; Type: CONSTRAINT; Schema: public; Owner: prisma_migration
--

ALTER TABLE ONLY public.waitlists
    ADD CONSTRAINT waitlists_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict HhkzwHC7CdF8GSen8AyBZyjxUpNgjMP0paQbt1fGRO3s5qRZsxPaNTIJg3OLUeJ

