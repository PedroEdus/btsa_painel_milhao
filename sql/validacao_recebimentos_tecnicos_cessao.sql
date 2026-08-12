-- Validacao: recebimento TECNICO no ato da cessao de direito.
-- Contexto: media de R$ 335k/venda recebidos na campanha nas vendas
-- ANTIGAS cedidas (validacao_cessoes.xlsx, bloco 3) - alto demais p/
-- lote. Suspeita: UAU registra baixa do saldo como recebimento ao
-- aprovar a cessao. Se confirmar:
--   a) esse valor NAO e dinheiro do cliente -> nao pode virar cupom
--      herdado (quando a heranca for aprovada pelo negocio);
--   b) cupons das vendas novas QUITADAS resgatadas na query principal
--      (11/08) precisam vir de pagamento real - bloco 3 confere.
-- Sinal de tecnico: Data_Rec no dia da manutencao/aprovacao da cessao
-- (ou depois, na venda antiga ja cancelada) e/ou Tipo_rec atipico.
-- SOMENTE LEITURA. Rodar na origem (BURITI-BD-02 via gateway).
-- Universo: obras 65-69, sem empresas 3/204/226/229/301/302,
-- cessoes aprovadas na campanha (DataMnt >= 01/07/2026).
-- Autor: Pedro (11/08/2026)

-- ------------------------------------------------------------------
-- 1) Venda ANTIGA: recebimentos da campanha por posicao temporal
--    vs data da cessao. 'No dia'/'depois' = forte suspeita de tecnico.
-- ------------------------------------------------------------------
SELECT
    CASE
        WHEN CAST(r.Data_Rec AS DATE) < CAST(vh.DataMnt_vhist AS DATE)
            THEN '1. Antes da cessao (pagamento real do cedente)'
        WHEN CAST(r.Data_Rec AS DATE) = CAST(vh.DataMnt_vhist AS DATE)
            THEN '2. NO DIA da cessao (suspeita tecnico)'
        ELSE '3. DEPOIS da cessao (venda ja cancelada - suspeita tecnico)'
    END                                                   AS Posicao,
    r.Tipo_rec,
    COUNT(*)                                              AS QtdLinhas,
    COUNT(DISTINCT CONCAT(r.Empresa_rec, '-', r.Obra_rec, '-', r.NumVend_rec)) AS QtdVendas,
    SUM(r.ValorConf_Rec + r.VlJurosParcConf_Rec + r.VlCorrecaoConf_Rec
      + r.VlAcresConf_Rec + r.VlTaxaBolConf_Rec + r.VlMultaConf_Rec
      + r.VlJurosConf_Rec + r.VlCorrecaoAtrConf_Rec
      - r.VlDescontoConf_Rec - r.ValDescontoCustaConf_Rec
      - r.ValDescontoImpostoConf_Rec - r.ValDescontoCondicionalConf_rec)
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
GROUP BY
    CASE
        WHEN CAST(r.Data_Rec AS DATE) < CAST(vh.DataMnt_vhist AS DATE)
            THEN '1. Antes da cessao (pagamento real do cedente)'
        WHEN CAST(r.Data_Rec AS DATE) = CAST(vh.DataMnt_vhist AS DATE)
            THEN '2. NO DIA da cessao (suspeita tecnico)'
        ELSE '3. DEPOIS da cessao (venda ja cancelada - suspeita tecnico)'
    END,
    r.Tipo_rec
ORDER BY Posicao, ValorRecebido DESC;

-- ------------------------------------------------------------------
-- 2) Venda NOVA: recebimentos por posicao vs data da cessao.
--    'Antes' e impossivel organicamente (venda nem existia) =
--    re-registro tecnico; 'no dia' = suspeito (transferencia de saldo).
-- ------------------------------------------------------------------
SELECT
    CASE
        WHEN CAST(r.Data_Rec AS DATE) < CAST(vh.DataMnt_vhist AS DATE)
            THEN '1. ANTES da cessao (venda nem existia - tecnico)'
        WHEN CAST(r.Data_Rec AS DATE) = CAST(vh.DataMnt_vhist AS DATE)
            THEN '2. NO DIA da cessao (suspeita tecnico/entrada)'
        ELSE '3. Depois da cessao (pagamento real do cessionario)'
    END                                                   AS Posicao,
    r.Tipo_rec,
    COUNT(*)                                              AS QtdLinhas,
    COUNT(DISTINCT CONCAT(r.Empresa_rec, '-', r.Obra_rec, '-', r.NumVend_rec)) AS QtdVendas,
    SUM(r.ValorConf_Rec + r.VlJurosParcConf_Rec + r.VlCorrecaoConf_Rec
      + r.VlAcresConf_Rec + r.VlTaxaBolConf_Rec + r.VlMultaConf_Rec
      + r.VlJurosConf_Rec + r.VlCorrecaoAtrConf_Rec
      - r.VlDescontoConf_Rec - r.ValDescontoCustaConf_Rec
      - r.ValDescontoImpostoConf_Rec - r.ValDescontoCondicionalConf_rec)
                                                          AS ValorRecebido
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
GROUP BY
    CASE
        WHEN CAST(r.Data_Rec AS DATE) < CAST(vh.DataMnt_vhist AS DATE)
            THEN '1. ANTES da cessao (venda nem existia - tecnico)'
        WHEN CAST(r.Data_Rec AS DATE) = CAST(vh.DataMnt_vhist AS DATE)
            THEN '2. NO DIA da cessao (suspeita tecnico/entrada)'
        ELSE '3. Depois da cessao (pagamento real do cessionario)'
    END,
    r.Tipo_rec
ORDER BY Posicao, ValorRecebido DESC;

-- ------------------------------------------------------------------
-- 3) As 128 vendas novas QUITADAS resgatadas na query principal:
--    cupons delas vem de pagamento real? Detalhe por venda com o
--    filtro EXATO da query principal (Tipo_rec <> '1').
--    ValorForaJanelaTecnica = recebido depois do dia da cessao
--    (dinheiro real do cessionario). Se ValorNoDiaOuAntes dominar,
--    o resgate precisa de filtro adicional antes de ir pro painel.
-- ------------------------------------------------------------------
SELECT
    vh.Empresa_vhist                                      AS Empresa,
    vh.Obra_vhist                                         AS Obra,
    vh.NumNovaVend_vhist                                  AS VendaNova,
    CONVERT(varchar(10), vh.DataMnt_vhist, 103)           AS DataCessao,
    SUM(IIF(CAST(r.Data_Rec AS DATE) <= CAST(vh.DataMnt_vhist AS DATE),
        r.ValorConf_Rec + r.VlJurosParcConf_Rec + r.VlCorrecaoConf_Rec
      + r.VlAcresConf_Rec + r.VlTaxaBolConf_Rec + r.VlMultaConf_Rec
      + r.VlJurosConf_Rec + r.VlCorrecaoAtrConf_Rec
      - r.VlDescontoConf_Rec - r.ValDescontoCustaConf_Rec
      - r.ValDescontoImpostoConf_Rec - r.ValDescontoCondicionalConf_rec, 0))
                                                          AS ValorNoDiaOuAntes,
    SUM(IIF(CAST(r.Data_Rec AS DATE) > CAST(vh.DataMnt_vhist AS DATE),
        r.ValorConf_Rec + r.VlJurosParcConf_Rec + r.VlCorrecaoConf_Rec
      + r.VlAcresConf_Rec + r.VlTaxaBolConf_Rec + r.VlMultaConf_Rec
      + r.VlJurosConf_Rec + r.VlCorrecaoAtrConf_Rec
      - r.VlDescontoConf_Rec - r.ValDescontoCustaConf_Rec
      - r.ValDescontoImpostoConf_Rec - r.ValDescontoCondicionalConf_rec, 0))
                                                          AS ValorForaJanelaTecnica
FROM VendaHist vh
INNER JOIN VendasRecebidas vr
    ON  vr.Empresa_vrec = vh.Empresa_vhist
    AND vr.Obra_VRec    = vh.Obra_vhist
    AND vr.Num_VRec     = vh.NumNovaVend_vhist
    AND vr.Status_Vrec  = 3        -- quitada (as resgatadas)
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
  AND r.Tipo_rec <> '1'            -- mesmo filtro da query principal
GROUP BY vh.Empresa_vhist, vh.Obra_vhist, vh.NumNovaVend_vhist, vh.DataMnt_vhist
ORDER BY ValorNoDiaOuAntes DESC;
