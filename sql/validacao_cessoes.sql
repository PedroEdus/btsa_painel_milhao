-- Validacao: cessoes de direito (contratos transferidos) na base do
-- Painel do Milhao. Pergunta de negocio: cessionario que paga durante a
-- campanha precisa aparecer na base (e como APTO se adimplente) - isso
-- ja acontece hoje?
--
-- Mecanismo UAU (vault, VendaHist.md + VendaDistrato.md):
--   - Cessao = VendaHist.TipoMnt_vhist = 2 (0 cancelamento, 1 renegociacao).
--   - Cessao gera VENDA NOVA: VendaHist.NumNovaVend_vhist = numero da venda
--     do cessionario. Parcelas/recebimentos da nova vida ficam no novo Num.
--   - Cessao NAO passa por VendaDistrato (medicao 06/08/2026: zero
--     sobreposicao) -> o NOT EXISTS da query principal nao derruba cessao.
--   - Vendas.DataCessao_Ven marca envolvimento com cessao (semantica exata
--     - venda antiga ou nova - e validada no bloco 4).
--   - SAC_GestaoClientes usa dbo.fn_UltimaVendaCessaoDireito pra percorrer
--     a cadeia de cessoes ate a venda vigente (bloco 6 confere se existe).
--
-- Hipotese a validar: venda NOVA ja entra na base principal (nasce em
-- Vendas com Status_Ven = 0); venda ANTIGA sai (deletada ou migrada para
-- VendasRecebidas). Risco real e ficar SEM ENCADEAMENTO antiga -> nova:
--   a) cupons acumulados do cedente nao seguem o contrato;
--   b) contrato do snapshot "some" na reexecucao (mesmo mecanismo suspeito
--      da investigacao dos 8 sem retorno, 06/08).
--
-- SOMENTE LEITURA. Rodar na origem (BURITI-BD-02 via gateway).
-- Universo: obras 65-69, sem empresas 3/204/226/229/301/302.
-- Autor: Pedro (11/08/2026)

-- ------------------------------------------------------------------
-- 1) Volumetria: cessoes aprovadas no universo, total x campanha
-- ------------------------------------------------------------------
SELECT
    COUNT(*)                                              AS CessoesAprovadas,
    SUM(IIF(vh.DataMnt_vhist >= '20260701', 1, 0))        AS CessoesNaCampanha,
    MIN(vh.DataMnt_vhist)                                 AS PrimeiraCessao,
    MAX(vh.DataMnt_vhist)                                 AS UltimaCessao
FROM VendaHist vh
WHERE vh.TipoMnt_vhist = 2
  AND vh.DataAprovacao_vhist IS NOT NULL
  AND LEFT(vh.Obra_vhist, 2) IN ('65','67','68','69')
  AND vh.Empresa_vhist NOT IN (3, 204, 226, 229, 301, 302);

-- ------------------------------------------------------------------
-- 2) Cessoes da campanha: onde estao venda ANTIGA e venda NOVA?
--    (Vendas x VendasRecebidas x sumiu, e com qual status)
-- ------------------------------------------------------------------
SELECT
    vh.Empresa_vhist                                      AS Empresa,
    vh.Obra_vhist                                         AS Obra,
    vh.NumVend_vhist                                      AS VendaAntiga,
    vh.NumNovaVend_vhist                                  AS VendaNova,
    CONVERT(varchar(10), vh.DataMnt_vhist, 103)           AS DataCessao,

    -- venda antiga
    CASE
        WHEN va.Num_Ven   IS NOT NULL THEN CONCAT('Vendas (status ',  va.Status_ven,  ')')
        WHEN var_.Num_VRec IS NOT NULL THEN CONCAT('VendasRecebidas (status ', var_.Status_Vrec, ')')
        ELSE 'SUMIU (nenhuma tabela)'
    END                                                   AS OndeVendaAntiga,

    -- venda nova
    CASE
        WHEN vn.Num_Ven   IS NOT NULL THEN CONCAT('Vendas (status ',  vn.Status_ven,  ')')
        WHEN vnr.Num_VRec IS NOT NULL THEN CONCAT('VendasRecebidas (status ', vnr.Status_Vrec, ')')
        ELSE 'NAO ENCONTRADA'
    END                                                   AS OndeVendaNova,

    -- venda nova passaria no WHERE da query principal?
    CASE
        WHEN COALESCE(vn.Status_ven, vnr.Status_Vrec) = 0
         AND NOT EXISTS (
                SELECT 1 FROM VendaDistrato vdd
                WHERE vdd.Empresa_vdd     = vh.Empresa_vhist
                  AND vdd.obra_vdd        = vh.Obra_vhist
                  AND vdd.NumVend_vdd     = vh.NumNovaVend_vhist
                  AND vdd.TipoAditivo_vdd = 0
                  AND vdd.StatusAprov_vdd = 1)
            THEN 'Sim'
        ELSE 'NAO'
    END                                                   AS NovaEntraNaBase

FROM VendaHist vh
LEFT JOIN Vendas va
    ON  va.Empresa_ven = vh.Empresa_vhist
    AND va.Obra_Ven    = vh.Obra_vhist
    AND va.Num_Ven     = vh.NumVend_vhist
LEFT JOIN VendasRecebidas var_
    ON  var_.Empresa_vrec = vh.Empresa_vhist
    AND var_.Obra_VRec    = vh.Obra_vhist
    AND var_.Num_VRec     = vh.NumVend_vhist
LEFT JOIN Vendas vn
    ON  vn.Empresa_ven = vh.Empresa_vhist
    AND vn.Obra_Ven    = vh.Obra_vhist
    AND vn.Num_Ven     = vh.NumNovaVend_vhist
LEFT JOIN VendasRecebidas vnr
    ON  vnr.Empresa_vrec = vh.Empresa_vhist
    AND vnr.Obra_VRec    = vh.Obra_vhist
    AND vnr.Num_VRec     = vh.NumNovaVend_vhist
WHERE vh.TipoMnt_vhist = 2
  AND vh.DataAprovacao_vhist IS NOT NULL
  AND vh.DataMnt_vhist >= '20260701'
  AND LEFT(vh.Obra_vhist, 2) IN ('65','67','68','69')
  AND vh.Empresa_vhist NOT IN (3, 204, 226, 229, 301, 302)
ORDER BY vh.DataMnt_vhist DESC;

-- ------------------------------------------------------------------
-- 3) Dinheiro em jogo: recebimentos da campanha pendurados na venda
--    ANTIGA de cessoes da campanha (cupons que nao seguem o cessionario
--    hoje) x recebimentos ja na venda NOVA
-- ------------------------------------------------------------------
SELECT
    resumo.Lado,
    COUNT(DISTINCT CONCAT(resumo.Empresa, '-', resumo.Obra, '-', resumo.Venda)) AS QtdVendas,
    SUM(resumo.ValorRecebido)                             AS ValorRecebidoCampanha
FROM (
    SELECT
        'Antiga (cedente)' AS Lado,
        vh.Empresa_vhist AS Empresa, vh.Obra_vhist AS Obra,
        vh.NumVend_vhist AS Venda,
        r.ValorConf_Rec + r.VlJurosParcConf_Rec + r.VlCorrecaoConf_Rec
          + r.VlAcresConf_Rec + r.VlTaxaBolConf_Rec + r.VlMultaConf_Rec
          + r.VlJurosConf_Rec + r.VlCorrecaoAtrConf_Rec
          - r.VlDescontoConf_Rec - r.ValDescontoCustaConf_Rec
          - r.ValDescontoImpostoConf_Rec - r.ValDescontoCondicionalConf_rec
          AS ValorRecebido
    FROM VendaHist vh
    INNER JOIN Recebidas r
        ON  r.Empresa_rec = vh.Empresa_vhist
        AND r.Obra_rec    = vh.Obra_vhist
        AND r.NumVend_rec = vh.NumVend_vhist
    WHERE vh.TipoMnt_vhist = 2
      AND vh.DataAprovacao_vhist IS NOT NULL
      AND vh.DataMnt_vhist >= '20260701'
      AND LEFT(vh.Obra_vhist, 2) IN ('65','67','68','69')
      AND vh.Empresa_vhist NOT IN (3, 204, 226, 229, 301, 302)
      AND CAST(r.Data_Rec AS DATE) >= '20260701'
      AND CAST(r.Data_Rec AS DATE) <  '20270101'
      AND r.Tipo_rec <> '1'

    UNION ALL

    SELECT
        'Nova (cessionario)',
        vh.Empresa_vhist, vh.Obra_vhist,
        vh.NumNovaVend_vhist,
        r.ValorConf_Rec + r.VlJurosParcConf_Rec + r.VlCorrecaoConf_Rec
          + r.VlAcresConf_Rec + r.VlTaxaBolConf_Rec + r.VlMultaConf_Rec
          + r.VlJurosConf_Rec + r.VlCorrecaoAtrConf_Rec
          - r.VlDescontoConf_Rec - r.ValDescontoCustaConf_Rec
          - r.ValDescontoImpostoConf_Rec - r.ValDescontoCondicionalConf_rec
    FROM VendaHist vh
    INNER JOIN Recebidas r
        ON  r.Empresa_rec = vh.Empresa_vhist
        AND r.Obra_rec    = vh.Obra_vhist
        AND r.NumVend_rec = vh.NumNovaVend_vhist
    WHERE vh.TipoMnt_vhist = 2
      AND vh.DataAprovacao_vhist IS NOT NULL
      AND vh.DataMnt_vhist >= '20260701'
      AND LEFT(vh.Obra_vhist, 2) IN ('65','67','68','69')
      AND vh.Empresa_vhist NOT IN (3, 204, 226, 229, 301, 302)
      AND CAST(r.Data_Rec AS DATE) >= '20260701'
      AND CAST(r.Data_Rec AS DATE) <  '20270101'
      AND r.Tipo_rec <> '1'
) AS resumo
GROUP BY resumo.Lado;

-- ------------------------------------------------------------------
-- 4) Semantica de DataCessao_Ven: preenchida na venda antiga, na nova
--    ou em ambas? (resolve ambiguidade do vault: fVendas exclui
--    IS NOT NULL como "cedidas", mas pode ser "originadas de cessao")
-- ------------------------------------------------------------------
SELECT
    IIF(vAnt.DataCessao_Ven IS NOT NULL, 1, 0)            AS AntigaTemDataCessao,
    IIF(vNov.DataCessao_Ven IS NOT NULL, 1, 0)            AS NovaTemDataCessao,
    COUNT(*)                                              AS Qtd
FROM VendaHist vh
LEFT JOIN Vendas vAnt
    ON  vAnt.Empresa_ven = vh.Empresa_vhist
    AND vAnt.Obra_Ven    = vh.Obra_vhist
    AND vAnt.Num_Ven     = vh.NumVend_vhist
LEFT JOIN Vendas vNov
    ON  vNov.Empresa_ven = vh.Empresa_vhist
    AND vNov.Obra_Ven    = vh.Obra_vhist
    AND vNov.Num_Ven     = vh.NumNovaVend_vhist
WHERE vh.TipoMnt_vhist = 2
  AND vh.DataAprovacao_vhist IS NOT NULL
  AND LEFT(vh.Obra_vhist, 2) IN ('65','67','68','69')
  AND vh.Empresa_vhist NOT IN (3, 204, 226, 229, 301, 302)
GROUP BY
    IIF(vAnt.DataCessao_Ven IS NOT NULL, 1, 0),
    IIF(vNov.DataCessao_Ven IS NOT NULL, 1, 0);

-- ------------------------------------------------------------------
-- 5) Cliente muda? Venda nova deve estar no nome do cessionario.
--    Amostra: 20 cessoes mais recentes da campanha.
--    (nomes = dado pessoal; usar so pra conferencia visual, nao exportar)
-- ------------------------------------------------------------------
SELECT TOP 20
    vh.Empresa_vhist                                      AS Empresa,
    vh.Obra_vhist                                         AS Obra,
    vh.NumVend_vhist                                      AS VendaAntiga,
    vh.NumNovaVend_vhist                                  AS VendaNova,
    CONVERT(varchar(10), vh.DataMnt_vhist, 103)           AS DataCessao,
    pAnt.Nome_pes                                         AS ClienteAntigo,
    pNov.Nome_pes                                         AS ClienteNovo
FROM VendaHist vh
LEFT JOIN Vendas vAnt
    ON  vAnt.Empresa_ven = vh.Empresa_vhist
    AND vAnt.Obra_Ven    = vh.Obra_vhist
    AND vAnt.Num_Ven     = vh.NumVend_vhist
LEFT JOIN VendasRecebidas vAntR
    ON  vAntR.Empresa_vrec = vh.Empresa_vhist
    AND vAntR.Obra_VRec    = vh.Obra_vhist
    AND vAntR.Num_VRec     = vh.NumVend_vhist
LEFT JOIN Vendas vNov
    ON  vNov.Empresa_ven = vh.Empresa_vhist
    AND vNov.Obra_Ven    = vh.Obra_vhist
    AND vNov.Num_Ven     = vh.NumNovaVend_vhist
LEFT JOIN Pessoas pAnt ON pAnt.cod_pes = COALESCE(vAnt.Cliente_Ven, vAntR.Cliente_VRec)
LEFT JOIN Pessoas pNov ON pNov.cod_pes = vNov.Cliente_Ven
WHERE vh.TipoMnt_vhist = 2
  AND vh.DataAprovacao_vhist IS NOT NULL
  AND vh.DataMnt_vhist >= '20260701'
  AND LEFT(vh.Obra_vhist, 2) IN ('65','67','68','69')
  AND vh.Empresa_vhist NOT IN (3, 204, 226, 229, 301, 302)
ORDER BY vh.DataMnt_vhist DESC;

-- ------------------------------------------------------------------
-- 6) fn_UltimaVendaCessaoDireito existe? (SAC_GestaoClientes usa pra
--    remapear cadeia de cessoes - candidata pra encadear cupons)
-- ------------------------------------------------------------------
SELECT name, type_desc, create_date, modify_date
FROM sys.objects
WHERE name LIKE '%CessaoDireito%';
