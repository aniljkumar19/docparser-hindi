--
-- PostgreSQL database dump
--

\restrict g3FeQEw1i5AZG6ktcMG2QSAYEZrqeOl4t410mKfwX7CcEXSx1ADBCMhVKFCbTww

-- Dumped from database version 15.14
-- Dumped by pg_dump version 15.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
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
-- Name: jobs; Type: TABLE; Schema: public; Owner: docuser
--

CREATE TABLE public.jobs (
    id character varying NOT NULL,
    status character varying,
    doc_type character varying,
    object_key character varying,
    api_key character varying,
    filename character varying,
    result json,
    meta json,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    tenant_id text
);


ALTER TABLE public.jobs OWNER TO docuser;

--
-- Name: tenants; Type: TABLE; Schema: public; Owner: docuser
--

CREATE TABLE public.tenants (
    id text NOT NULL,
    name text,
    contact_email text,
    stripe_customer_id text,
    stripe_subscription_id text,
    stripe_item_parse text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.tenants OWNER TO docuser;

--
-- Data for Name: jobs; Type: TABLE DATA; Schema: public; Owner: docuser
--

COPY public.jobs (id, status, doc_type, object_key, api_key, filename, result, meta, created_at, updated_at, tenant_id) FROM stdin;
job_957efa201a9f	succeeded	invoice	uploads/87be98744b634fc3ad018babda8eb4b9_sample_invoice.txt	dev_123	sample_invoice.txt	{"invoice_number": null, "date": null, "seller": {}, "buyer": {}, "currency": "INR", "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 22}	2025-09-06 17:01:20.569294+00	2025-09-06 17:01:21.562736+00	\N
job_aa78028f2dc4	failed	unknown	uploads/9abc08c07bb048ba8eea060c4748104e/sample_invoice.txt	dev_123	sample_invoice.txt	null	{"error": "name 'logger' is not defined"}	2025-09-07 04:53:59.941307+00	2025-09-07 04:54:00.967465+00	tenant_demo
job_1b31b5c6b2fb	succeeded	invoice	uploads/963d64b05d9e437589dca086366371fc_sample_invoice.txt	dev_123	sample_invoice.txt	{"invoice_number": null, "date": null, "seller": {}, "buyer": {}, "currency": "INR", "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 21}	2025-09-06 17:01:28.449893+00	2025-09-06 17:01:29.376821+00	\N
job_0e982bb9a75e	failed	invoice	uploads/e63ee53f1ee94876bf2a99473b34c790/Commitment_Rev_2_55-19801.pdf	dev_123	Commitment Rev 2_55-19801.pdf	\N	{"error": "name 'filename' is not defined"}	2025-09-06 21:16:17.878045+00	2025-09-06 21:16:18.784294+00	\N
job_e0c05ba9e184	succeeded	invoice	uploads/b52b459717344f2fb1a5ae176a2d6af0_sample_invoice.txt	dev_123	sample_invoice.txt	{"invoice_number": null, "date": null, "seller": {}, "buyer": {}, "currency": "INR", "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 22}	2025-09-06 17:02:15.137693+00	2025-09-06 17:02:16.063637+00	\N
job_9c027a1b85a6	succeeded	invoice	uploads/539941f1c23748e1bacabfad3818b59f_Gagan Birth Certificate.pdf	dev_123	Gagan Birth Certificate.pdf	{"invoice_number": null, "date": null, "seller": {}, "buyer": {}, "currency": "INR", "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 24}	2025-09-06 17:19:48.592806+00	2025-09-06 17:19:49.512768+00	\N
job_828b3bbc08e0	succeeded	invoice	uploads/a9636d42e96b4fb0b82cad123aab0120_Gagan Birth Certificate.pdf	dev_123	Gagan Birth Certificate.pdf	{"invoice_number": null, "date": null, "seller": {}, "buyer": {}, "currency": "INR", "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 23}	2025-09-06 17:22:12.514075+00	2025-09-06 17:22:13.427112+00	\N
job_1280876264f6	failed	invoice	uploads/749fcd6136534498ae2cebbc29458a92/sample_invoice.txt	dev_123	sample_invoice.txt	\N	{"error": "name 'filename' is not defined"}	2025-09-07 04:02:13.999726+00	2025-09-07 04:02:14.991243+00	tenant_demo
job_8cd5d59e9d31	failed	invoice	uploads/52ff9b3912da4590b81552b680ff8237_Gagan Birth Certificate.pdf	dev_123	Gagan Birth Certificate.pdf	\N	{"error": "'str' object is not callable"}	2025-09-06 19:07:28.431235+00	2025-09-06 19:07:29.403322+00	\N
job_79f50cd6cdeb	failed	invoice	uploads/a0016e12c7d54e89bf4a41b2d26ac814_Gagan address proof.pdf	dev_123	Gagan address proof.pdf	\N	{"error": "'str' object is not callable"}	2025-09-06 19:09:14.364241+00	2025-09-06 19:09:15.291676+00	\N
job_d081ce71f013	succeeded	invoice	uploads/ed2f0e102746431e8093cd5fde766ad6_Gagan address proof.pdf	dev_123	Gagan address proof.pdf	{"invoice_number": {"value": "est", "confidence": 0.9}, "date": null, "seller": {}, "buyer": {}, "currency": "INR", "subtotal": 0.0, "taxes": [], "total": null, "line_items": [{"desc": "Total therms used", "qty": 1.0, "unit_price": 0.0, "amount": 0.0}], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 212}	2025-09-06 19:18:51.969891+00	2025-09-06 19:18:52.902839+00	\N
job_29e4b605f7d2	failed	invoice	uploads/7eca0974471f4c4abf3b40819a2a19ea/sample_invoice.txt	dev_123	sample_invoice.txt	\N	{"error": "name 'filename' is not defined"}	2025-09-07 04:24:40.43662+00	2025-09-07 04:24:41.432388+00	tenant_demo
job_b7052e55ac8b	succeeded	invoice	uploads/d7fcd2b421c14cada947f1a2dc2760b0/Gagan_Birth_Certificate.pdf	dev_123	Gagan Birth Certificate.pdf	{"invoice_number": null, "date": null, "seller": {}, "buyer": {}, "currency": null, "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": ["Unsupported document type: unknown"]}	{"pages": 1, "ocr_used": false, "processing_ms": 24, "detected_doc_type": "unknown"}	2025-09-06 19:48:02.281985+00	2025-09-06 19:48:03.21758+00	\N
job_6730247f4586	failed	invoice	uploads/feb75a4e98f54258a6c26dc9db160b88/sample_invoice.txt	dev_123	sample_invoice.txt	\N	{"error": "name 'filename' is not defined"}	2025-09-06 21:15:54.09115+00	2025-09-06 21:15:55.014349+00	\N
job_5871deb5175c	failed	unknown	uploads/35f962ce90cc4f4d88c6920ae8de1239/sample_invoice.txt	dev_123	sample_invoice.txt	null	{"error": "name 'logger' is not defined"}	2025-09-07 05:09:30.218628+00	2025-09-07 05:09:31.182069+00	tenant_demo
job_e5f26b62d735	failed	unknown	uploads/5fc80d9297574770bd06166afead36f7/sample_invoice.txt	dev_123	sample_invoice.txt	null	{"error": "name 'logger' is not defined"}	2025-09-07 04:51:55.186127+00	2025-09-07 04:51:56.14306+00	tenant_demo
job_140231a754d5	succeeded	unknown	uploads/eb3a7d12b2324cd58243745dd62d5771/sample_receipt.txt	dev_123	sample_receipt.txt	{"invoice_number": null, "date": null, "seller": {}, "buyer": {}, "currency": null, "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": ["Unsupported or unknown document type"]}	{"pages": 1, "ocr_used": false, "processing_ms": 39, "detected_doc_type": "unknown", "source_filename": "sample_receipt.txt"}	2025-09-07 20:02:59.266176+00	2025-09-07 20:03:00.244447+00	tenant_demo
job_7edd55a4a842	succeeded	unknown	uploads/186b7e7a73b64ce38dbcede4501ea40d/sample_invoice.txt	dev_123	sample_invoice.txt	{"invoice_number": null, "date": null, "seller": {}, "buyer": {}, "currency": null, "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": ["Unsupported document type: unknown"]}	{"pages": 1, "ocr_used": false, "processing_ms": 23, "detected_doc_type": "unknown", "source_filename": "sample_invoice.txt"}	2025-09-07 05:13:24.428389+00	2025-09-07 05:13:25.405998+00	tenant_demo
job_263646115414	succeeded	unknown	uploads/87d6300fbecb4e0d9395f0aa5512237e/sample_receipt.txt	dev_123	sample_receipt.txt	{"invoice_number": null, "date": null, "seller": {}, "buyer": {}, "currency": null, "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": ["Unsupported or unknown document type"]}	{"pages": 1, "ocr_used": false, "processing_ms": 22, "detected_doc_type": "unknown", "source_filename": "sample_receipt.txt"}	2025-09-07 20:03:06.71104+00	2025-09-07 20:03:07.614073+00	tenant_demo
job_80402cb650b2	failed	invoice	uploads/e610366bf1744745a28edad20f43f0b4/sample_receipt.txt	dev_123	sample_receipt.txt	\N	{"error": "cannot access local variable 'inv' where it is not associated with a value"}	2025-09-07 20:29:04.982152+00	2025-09-07 20:29:05.918743+00	tenant_demo
job_b08b00fb8bdc	failed	invoice	uploads/e076352b16bc45a6bf1717b0d0f426cd/sample_receipt.txt	dev_123	sample_receipt.txt	\N	{"error": "match() missing 1 required positional argument: 'string'"}	2025-09-07 20:44:20.629995+00	2025-09-07 20:44:21.575239+00	tenant_demo
job_221370d475cc	queued	invoice	uploads/88e93acff4924d76857393640c67c386/sample_receipt.txt	dev_123	sample_receipt.txt	\N	\N	2025-09-07 21:12:00.665007+00	2025-09-07 21:12:00.665654+00	tenant_demo
job_92400dc3f6e0	succeeded	invoice	uploads/367fb07f29b3488289944c12bf1d42f5/sample_receipt.txt	dev_123	sample_receipt.txt	{"invoice_number": null, "date": {"value": "2024-11-01", "confidence": 0.8}, "seller": {}, "buyer": {}, "currency": "INR", "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 0, "detected_doc_type": "invoice", "source_filename": "sample_receipt.txt"}	2025-09-07 21:06:28.902691+00	2025-09-07 21:06:29.836894+00	tenant_demo
job_f18b8544b8a0	succeeded	receipt	uploads/b18fa3e8bfbc4c2184bb25f5f6bb4875/sample_receipt.txt	dev_123	sample_receipt.txt	{"invoice_number": null, "date": null, "seller": {}, "buyer": {}, "currency": null, "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": ["Unsupported or unknown document type"]}	{"pages": 1, "ocr_used": false, "processing_ms": 0, "detected_doc_type": "receipt", "source_filename": "sample_receipt.txt"}	2025-09-07 21:49:50.116965+00	2025-09-07 21:49:51.11602+00	tenant_demo
job_3eb0374675d0	succeeded	receipt	uploads/2a825ff754bc46f8bc8ed5eeda09a85d/sample_receipt.txt	dev_123	sample_receipt.txt	{"invoice_number": null, "date": null, "seller": {}, "buyer": {}, "currency": null, "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": ["Unsupported or unknown document type"]}	{"pages": 1, "ocr_used": false, "processing_ms": 0, "detected_doc_type": "receipt", "source_filename": "sample_receipt.txt"}	2025-09-07 21:52:04.019707+00	2025-09-07 21:52:04.938467+00	tenant_demo
job_c9ffe97eeb3d	succeeded	receipt	uploads/420fe6f1a58f4cc5b1b26e21f768e89c/sample_receipt.txt	dev_123	sample_receipt.txt	{"invoice_number": null, "date": null, "seller": {}, "buyer": {}, "currency": null, "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": ["Unsupported or unknown document type"]}	{"pages": 1, "ocr_used": false, "processing_ms": 0, "detected_doc_type": "receipt", "source_filename": "sample_receipt.txt"}	2025-09-07 22:03:26.007633+00	2025-09-07 22:03:26.963292+00	tenant_demo
job_4feda62cbe76	succeeded	receipt	uploads/a289ccd29724442c8c01b7f4ac7ad3a6/sample_receipt.txt	dev_123	sample_receipt.txt	{"invoice_number": null, "date": null, "seller": {}, "buyer": {}, "currency": null, "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": ["Unsupported or unknown document type"]}	{"pages": 1, "ocr_used": false, "processing_ms": 0, "detected_doc_type": "receipt", "source_filename": "sample_receipt.txt"}	2025-09-08 01:26:43.121636+00	2025-09-08 01:26:44.109255+00	tenant_demo
job_1a0615e10a8f	succeeded	receipt	uploads/f6795c7c18f541788c59636bde3517eb/sample_receipt.txt	dev_123	sample_receipt.txt	{"merchant": {"name": "SuperMart City Center"}, "date": {"value": "2024-11-01", "confidence": 0.7}, "currency": "INR", "subtotal": 4.48, "taxes": [{"type": "GST", "amount": 0.22}], "total": 4.7, "line_items": [], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 0, "detected_doc_type": "receipt", "source_filename": "sample_receipt.txt"}	2025-09-08 01:37:26.05539+00	2025-09-08 01:37:27.034538+00	tenant_demo
job_e4cc74bb85bb	succeeded	receipt	uploads/d5159598b2ef4385b466f2b89e3ab9f9/sample_receipt.txt	dev_123	sample_receipt.txt	{"merchant": {"name": "SuperMart City Center"}, "date": {"value": "2024-11-01", "confidence": 0.7}, "currency": "INR", "subtotal": 4.48, "taxes": [{"type": "GST", "amount": 0.22}], "total": 4.7, "line_items": [{"desc": "Bread", "qty": 1, "unit_price": 2.99, "amount": 2.99}, {"desc": "Milk", "qty": 1, "unit_price": 1.49, "amount": 1.49}], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 1, "detected_doc_type": "receipt", "doc_type_scores": {"invoice": 0, "birth_certificate": 0, "receipt": 2, "utility_bill": 0}, "doc_type_confidence": 2, "source_filename": "sample_receipt.txt"}	2025-09-08 03:25:44.340357+00	2025-09-08 03:25:45.249072+00	tenant_demo
job_25c04dd86899	succeeded	utility_bill	uploads/36e2a982daa74a97a930f1480890c760/sample_utility.txt	dev_123	sample_utility.txt	{"provider": {"name": "City Electric Co."}, "account_number": "12345-ABCD", "service_period": "2024/10/01 - 2024/10/31", "due_date": "2024-11-15", "amount_due": 1284.5, "currency": "INR", "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 0, "detected_doc_type": "utility_bill", "source_filename": "sample_utility.txt"}	2025-09-08 01:51:19.38998+00	2025-09-08 01:51:20.356704+00	tenant_demo
job_27b2f8f18a13	succeeded	receipt	uploads/3ffc2263930e4bca88a03bcbe5ff97aa/sample_receipt.txt	dev_123	sample_receipt.txt	\N	{"pages": 1, "ocr_used": false, "processing_ms": 1, "detected_doc_type": "receipt", "source_filename": "sample_receipt.txt"}	2025-09-08 02:00:34.386541+00	2025-09-08 02:00:35.305385+00	tenant_demo
job_7ac71f071fec	succeeded	receipt	uploads/2e26824ddcce4d70addb1b9fbe5e1ece/sample_receipt.txt	dev_123	sample_receipt.txt	{"merchant": {"name": "SuperMart City Center"}, "date": {"value": "2024-11-01", "confidence": 0.7}, "currency": "INR", "subtotal": 4.48, "taxes": [{"type": "GST", "amount": 0.22}], "total": 4.7, "line_items": [{"desc": "Bread", "qty": 1, "unit_price": 2.99, "amount": 2.99}, {"desc": "Milk", "qty": 1, "unit_price": 1.49, "amount": 1.49}], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 1, "detected_doc_type": "receipt", "source_filename": "sample_receipt.txt"}	2025-09-08 02:08:32.027115+00	2025-09-08 02:08:32.941135+00	tenant_demo
job_b5f892de7a52	queued	invoice	uploads/2fccb147ff3e4ea18c5638d0817ebbe1/sample_receipt.txt	dev_123	sample_receipt.txt	\N	\N	2025-09-08 03:10:29.016109+00	2025-09-08 03:10:29.01932+00	tenant_demo
job_bf557d79b9cc	succeeded	unknown	uploads/9efbc899853440f7b20975087bb0969a/Gagan_Birth_Certificate.pdf	dev_123	Gagan Birth Certificate.pdf	{"invoice_number": null, "date": null, "seller": {}, "buyer": {}, "currency": null, "subtotal": null, "taxes": [], "total": null, "line_items": [], "warnings": ["Unsupported or unknown document type"]}	{"pages": 1, "ocr_used": false, "processing_ms": 2, "detected_doc_type": "unknown", "doc_type_scores": {"invoice": 0, "birth_certificate": 0, "receipt": 0, "utility_bill": 0}, "doc_type_confidence": 0, "source_filename": "Gagan Birth Certificate.pdf"}	2025-09-08 03:38:30.855036+00	2025-09-08 03:38:31.794045+00	tenant_demo
job_c8101d5d290e	succeeded	receipt	uploads/16fba428d56b44aabce90913fa8333f8/sample_receipt.txt	dev_123	sample_receipt.txt	{"merchant": {"name": "SuperMart City Center"}, "date": {"value": "2024-11-01", "confidence": 0.7}, "currency": "INR", "subtotal": 4.48, "taxes": [{"type": "GST", "amount": 0.22}], "total": 4.7, "line_items": [{"desc": "Bread", "qty": 1, "unit_price": 2.99, "amount": 2.99}, {"desc": "Milk", "qty": 1, "unit_price": 1.49, "amount": 1.49}], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 1, "detected_doc_type": "receipt", "doc_type_scores": {"invoice": 0, "birth_certificate": 0, "receipt": 2, "utility_bill": 0}, "doc_type_confidence": 2, "source_filename": "sample_receipt.txt"}	2025-09-08 03:19:54.45145+00	2025-09-08 03:19:55.430649+00	tenant_demo
job_7bc07cc8bc10	succeeded	invoice	uploads/a4aae8d6e7b543b98850f1273365a577/sample_invoice.txt	dev_123	sample_invoice.txt	{"invoice_number": null, "date": {"value": "2025-09-01", "confidence": 0.8}, "seller": {"gstin": "29ABCDE1234F1Z5"}, "buyer": {"gstin": "27PQRSX5678L1Z2"}, "currency": "INR", "subtotal": 12500.0, "taxes": [], "total": null, "line_items": [{"desc": "Item A", "qty": 10.0, "unit_price": 1000.0, "amount": 10000.0}, {"desc": "Item B", "qty": 5.0, "unit_price": 500.0, "amount": 2500.0}], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 1, "detected_doc_type": "invoice", "doc_type_scores": {"invoice": 2, "birth_certificate": 0, "receipt": 2, "utility_bill": 0}, "doc_type_confidence": 2, "source_filename": "sample_invoice.txt"}	2025-09-08 03:42:52.643641+00	2025-09-08 03:42:53.564787+00	tenant_demo
job_f508c62852eb	succeeded	invoice	uploads/9954d6c6364241eab8c6c8630fe50ded/sample_invoice.txt	dev_123	sample_invoice.txt	{"invoice_number": null, "date": {"value": "2025-09-01", "confidence": 0.8}, "seller": {"gstin": "29ABCDE1234F1Z5"}, "buyer": {"gstin": "27PQRSX5678L1Z2"}, "currency": "INR", "subtotal": 12500.0, "taxes": [], "total": null, "line_items": [{"desc": "Item A", "qty": 10.0, "unit_price": 1000.0, "amount": 10000.0}, {"desc": "Item B", "qty": 5.0, "unit_price": 500.0, "amount": 2500.0}], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 1, "detected_doc_type": "invoice", "doc_type_scores": {"invoice": 2, "birth_certificate": 0, "receipt": 2, "utility_bill": 0, "bank_statement": 0}, "doc_type_confidence": 2, "source_filename": "sample_invoice.txt"}	2025-09-28 15:23:19.687445+00	2025-09-28 15:23:20.693935+00	tenant_demo
job_768b9b3c56c3	succeeded	invoice	uploads/03a82631ea5b42bc98a609c20546220f/sample_invoice.txt	dev_123	sample_invoice.txt	{"invoice_number": null, "date": {"value": "2025-09-01", "confidence": 0.8}, "seller": {"gstin": "29ABCDE1234F1Z5"}, "buyer": {"gstin": "27PQRSX5678L1Z2"}, "currency": "INR", "subtotal": 12500.0, "taxes": [], "total": null, "line_items": [{"desc": "Item A", "qty": 10.0, "unit_price": 1000.0, "amount": 10000.0}, {"desc": "Item B", "qty": 5.0, "unit_price": 500.0, "amount": 2500.0}], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 1, "detected_doc_type": "invoice", "doc_type_scores": {"invoice": 2, "birth_certificate": 0, "receipt": 2, "utility_bill": 0, "bank_statement": 0}, "doc_type_confidence": 2, "source_filename": "sample_invoice.txt"}	2025-09-28 15:24:48.211773+00	2025-09-28 15:24:49.155125+00	tenant_demo
job_f6942f69bef4	succeeded	invoice	uploads/2f039991d3a04a21b4cf077522c453f9/sample_invoice.txt	dev_123	sample_invoice.txt	{"invoice_number": null, "date": {"value": "2025-09-01", "confidence": 0.8}, "seller": {"gstin": "29ABCDE1234F1Z5"}, "buyer": {"gstin": "27PQRSX5678L1Z2"}, "currency": "INR", "subtotal": 12500.0, "taxes": [], "total": null, "line_items": [{"desc": "Item A", "qty": 10.0, "unit_price": 1000.0, "amount": 10000.0}, {"desc": "Item B", "qty": 5.0, "unit_price": 500.0, "amount": 2500.0}], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 1, "detected_doc_type": "invoice", "doc_type_scores": {"invoice": 2, "birth_certificate": 0, "receipt": 2, "utility_bill": 0, "bank_statement": 0}, "doc_type_confidence": 2, "source_filename": "sample_invoice.txt"}	2025-09-28 15:40:46.934615+00	2025-09-28 15:40:47.885744+00	tenant_demo
job_9542c9804289	succeeded	invoice	uploads/e6f08182f00c4229abbb9208a427c26b/sample_invoice.txt	dev_123	sample_invoice.txt	{"invoice_number": null, "date": {"value": "2025-09-01", "confidence": 0.8}, "seller": {"gstin": "29ABCDE1234F1Z5"}, "buyer": {"gstin": "27PQRSX5678L1Z2"}, "currency": "INR", "subtotal": 12500.0, "taxes": [], "total": null, "line_items": [{"desc": "Item A", "qty": 10.0, "unit_price": 1000.0, "amount": 10000.0}, {"desc": "Item B", "qty": 5.0, "unit_price": 500.0, "amount": 2500.0}], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 1, "detected_doc_type": "invoice", "doc_type_scores": {"invoice": 2, "birth_certificate": 0, "receipt": 2, "utility_bill": 0, "bank_statement": 0}, "doc_type_confidence": 2, "source_filename": "sample_invoice.txt"}	2025-09-28 16:02:18.782347+00	2025-09-28 16:02:19.777616+00	tenant_demo
job_55a803219110	succeeded	invoice	uploads/65d50cbab7ed4a9bb70fa24939fb74fc/sample_invoice.txt	dev_123	sample_invoice.txt	{"invoice_number": null, "date": {"value": "2025-09-01", "confidence": 0.8}, "seller": {"gstin": "29ABCDE1234F1Z5"}, "buyer": {"gstin": "27PQRSX5678L1Z2"}, "currency": "INR", "subtotal": 12500.0, "taxes": [], "total": null, "line_items": [{"desc": "Item A", "qty": 10.0, "unit_price": 1000.0, "amount": 10000.0}, {"desc": "Item B", "qty": 5.0, "unit_price": 500.0, "amount": 2500.0}], "warnings": []}	{"pages": 1, "ocr_used": false, "processing_ms": 1, "detected_doc_type": "invoice", "doc_type_scores": {"invoice": 2, "birth_certificate": 0, "receipt": 2, "utility_bill": 0, "bank_statement": 0}, "doc_type_confidence": 2, "source_filename": "sample_invoice.txt"}	2025-09-28 16:08:51.368002+00	2025-09-28 16:08:52.304816+00	tenant_demo
\.


--
-- Data for Name: tenants; Type: TABLE DATA; Schema: public; Owner: docuser
--

COPY public.tenants (id, name, contact_email, stripe_customer_id, stripe_subscription_id, stripe_item_parse, created_at) FROM stdin;
tenant_demo	Demo Co	demo@example.com	cus_T0ZcBJAi6VyVBn	sub_1S4YSx8NTZn5kH2bZHrJVNrH	si_T0ZclhCEbFO62R	2025-09-07 02:36:17.21177+00
\.


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: docuser
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: docuser
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict g3FeQEw1i5AZG6ktcMG2QSAYEZrqeOl4t410mKfwX7CcEXSx1ADBCMhVKFCbTww

