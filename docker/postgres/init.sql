-- =============================================================================
-- Roda UMA vez, na primeira subida do PostgreSQL (volume vazio).
-- Para rodar de novo: apague o volume com "down -v" (isso apaga tudo).
-- =============================================================================

-- Um banco para cada serviço da plataforma
CREATE DATABASE metastore;  -- catálogo do Hive Metastore
CREATE DATABASE airflow;    -- estado do Airflow (execuções, logs de tarefas)
CREATE DATABASE metabase;   -- configuração do Metabase (perguntas, painéis)
CREATE DATABASE fonte;      -- sistema de origem simulado, lido pelo pipeline

-- -----------------------------------------------------------------------------
-- Banco "fonte": imita o banco transacional de um sistema de vendas.
-- -----------------------------------------------------------------------------
\connect fonte

CREATE SCHEMA vendas;

-- Sem chave primária de propósito: o sistema de origem tem duplicatas,
-- e tratá-las é trabalho da camada silver.
CREATE TABLE vendas.pedidos (
    id_pedido  integer,
    cliente    varchar(60),
    uf         varchar(5),
    valor      numeric(10, 2),
    status     varchar(20),
    criado_em  timestamp
);

-- 1.000 pedidos espalhados em cerca de 30 dias
INSERT INTO vendas.pedidos (id_pedido, cliente, uf, valor, status, criado_em)
SELECT
    g,
    'Cliente ' || (g % 120 + 1),
    (ARRAY['RN', 'CE', 'PB', 'PE', 'BA', 'SP', 'RJ', 'MG'])[g % 8 + 1],
    round((20 + (g * 37 % 480) + (g % 7) * 0.13)::numeric, 2),
    (ARRAY['pago', 'pago', 'pago', 'cancelado', 'pendente'])[g % 5 + 1],
    timestamp '2026-09-01 08:00' + g * interval '43 minutes'
FROM generate_series(1, 1000) AS g;

-- Sujeira proposital, para a camada silver limpar:
-- 1) linhas duplicadas
INSERT INTO vendas.pedidos
SELECT * FROM vendas.pedidos WHERE id_pedido % 50 = 0;

-- 2) UF em minúsculas e com espaços
UPDATE vendas.pedidos SET uf = ' ' || lower(uf) || ' ' WHERE id_pedido % 97 = 0;

-- 3) status com maiúsculas
UPDATE vendas.pedidos SET status = upper(status) WHERE id_pedido % 89 = 0;
