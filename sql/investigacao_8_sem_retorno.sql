-- Investigacao: 8 contratos do snapshot de 31/07 sem retorno na apuracao
-- retroativa v2 (que nao filtra status nem distrato). Suspeita: venda
-- deletada/recriada por manutencao entre 31/07 e a execucao (renegociacao
-- e cessao podem gerar nova venda - VendaHist.NumNovaVend_vhist).
-- Materialidade: todos com 0 cupons na foto - nao afetam a lista de
-- elegiveis. Investigacao e para entender o mecanismo, nao urgente.
-- SOMENTE LEITURA. Rodar na origem (BURITI-BD-02 via gateway).
-- Autor: Pedro (06/08/2026)

-- Chaves em tabela temporaria para reuso nos 3 blocos
DECLARE @chaves TABLE (Empresa smallint, Obra varchar(20), Venda int);
INSERT INTO @chaves VALUES
    (7,   '68328', 25498),
    (352, '67105', 5790),
    (401, '67402', 2222),
    (350, '67101', 4766),
    (33,  '68388', 1814),
    (10,  '68306', 2010),
    (352, '67105', 5785),
    (353, '67106', 1434);

-- 1) A venda ainda existe em alguma das duas tabelas?
SELECT 'Vendas' AS Fonte, v.Empresa_ven, v.Obra_ven, v.Num_Ven, v.Status_ven
FROM Vendas v
INNER JOIN @chaves c
    ON  c.Empresa = v.Empresa_ven
    AND c.Obra    = v.Obra_ven
    AND c.Venda   = v.Num_Ven

UNION ALL

SELECT 'VendasRecebidas', vr.Empresa_vrec, vr.Obra_VRec, vr.Num_VRec, vr.Status_Vrec
FROM VendasRecebidas vr
INNER JOIN @chaves c
    ON  c.Empresa = vr.Empresa_vrec
    AND c.Obra    = vr.Obra_VRec
    AND c.Venda   = vr.Num_VRec;

-- 2) Historico de manutencao: renegociacao/cessao gerou nova venda?
SELECT
    vh.Empresa_vhist,
    vh.Obra_vhist,
    vh.NumVend_vhist,
    vh.Num_vhist,
    vh.TipoMnt_vhist,        -- 0 cancelamento / 1 renegociacao / 2 cessao
    vh.DataMnt_vhist,
    vh.DataAprovacao_vhist,
    vh.NumNovaVend_vhist     -- nova venda gerada (cessao/renegociacao)
FROM VendaHist vh
INNER JOIN @chaves c
    ON  c.Empresa = vh.Empresa_vhist
    AND c.Obra    = vh.Obra_vhist
    AND c.Venda   = vh.NumVend_vhist
ORDER BY vh.Empresa_vhist, vh.NumVend_vhist, vh.Num_vhist;

-- 3) Distrato registrado para essas vendas?
SELECT
    vd.Empresa_vdd,
    vd.Obra_vdd,
    vd.NumVend_vdd,
    vd.TipoAditivo_vdd,
    vd.StatusAprov_vdd,
    vd.DataCad_vdd,
    vd.DataAprov_vdd,
    vd.CategDistrato_vdd
FROM VendaDistrato vd
INNER JOIN @chaves c
    ON  c.Empresa = vd.Empresa_vdd
    AND c.Obra    = vd.Obra_vdd
    AND c.Venda   = vd.NumVend_vdd
ORDER BY vd.Empresa_vdd, vd.NumVend_vdd, vd.DataCad_vdd;
