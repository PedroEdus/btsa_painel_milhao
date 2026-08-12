-- ============================================================
-- RESULTADO (rodado 06/08/2026, origem): HIPOTESE REFUTADA.
--   Bloco 1: 127.649 linhas | 1.541 com DataCad >= Data_Rec (1,2%)
--            | 126.108 com DataCad < Data_Rec (98,8%).
--   Blocos 2 e 4: vazios (nenhum pagamento de julho com DataCad em agosto).
--   Conclusao: DataCad_Rec NAO e a data de processamento da baixa
--   (aparenta ser herdada do cadastro da parcela/contrato). Nao serve
--   para detectar baixa atrasada. De-para volta a ser snapshot 31/07 ×
--   reexecucao da apuracao.
--   Bloco 3 (monitor por Data_Rec) SEGUE VALIDO. Medicao 06/08:
--   28/07=2.832 | 29/07=3.210 | 30/07=5.101 | 31/07=7.405 recebimentos.
--   Rodar de novo e comparar: igual = base fechou.
-- ============================================================

-- Validacao da semantica de DataCad_Rec (Recebidas) - SOMENTE LEITURA
-- Hipotese (mapa Conciliacao Bancaria 2026-07, armadilha 5: o UAU
--   reprocessa o passado, cargas por DataCad): DataCad_Rec = data em que a
--   linha nasceu em Recebidas (processamento da baixa); Data_Rec = data
--   real do pagamento. Se confirmada:
--   (1) DataCad_Rec >= Data_Rec na quase totalidade das linhas;
--   (2) pagamentos de 30-31/07 baixados em agosto aparecem com
--       DataCad_Rec >= 01/08.
-- Uso: rodar na origem (BURITI-BD-02 via gateway). Blocos independentes.
-- O bloco 3 e o monitor de completude: rodar 2x com intervalo de algumas
--   horas; se os numeros estabilizarem, as baixas do fechamento terminaram.
-- Sem dados pessoais na saida (chaves de venda apenas, no bloco 4).
-- Autor: Pedro (04/08/2026)

DECLARE @IniJulho date = '20260701';
DECLARE @Corte    date = '20260801';   -- primeiro dia apos o fechamento

-- --------------------------------------------------------
-- 1) Sanidade geral: DataCad_Rec vs Data_Rec na campanha.
-- Esperado: CadMenorQueRec ~ 0. Se vier relevante, a hipotese
-- cai e a flag [Baixa Pos Fechamento] nao pode ser usada.
-- --------------------------------------------------------
SELECT
    COUNT(*)                                                        [TotalLinhas],
    SUM(IIF(CAST(DataCad_Rec AS DATE) >= CAST(Data_Rec AS DATE), 1, 0)) [CadMaiorIgualRec],
    SUM(IIF(CAST(DataCad_Rec AS DATE) <  CAST(Data_Rec AS DATE), 1, 0)) [CadMenorQueRec],
    MAX(CAST(DataCad_Rec AS DATE))                                  [UltimoCadastro]
FROM Recebidas
WHERE CAST(Data_Rec AS DATE) >= @IniJulho
  AND LEFT(Obra_rec, 2) IN ('65','67','68','69');

-- --------------------------------------------------------
-- 2) Baixas tardias do fechamento: pagamentos com Data_Rec em julho
-- cuja linha foi cadastrada a partir de 01/08, por dia de cadastro.
-- Esperado: concentracao em 01-05/08 (baixas de sab/dom/seg atrasadas).
-- E o conjunto exato que o snapshot de 31/07 nao viu.
-- --------------------------------------------------------
SELECT
    CAST(DataCad_Rec AS DATE)                                       [DiaCadastro],
    COUNT(*)                                                        [QtdRecebimentos],
    COUNT(DISTINCT CONCAT(Empresa_rec, '-', Obra_rec, '-', NumVend_rec)) [QtdVendas],
    SUM((
          ValorConf_Rec
        + VlJurosParcConf_Rec
        + VlCorrecaoConf_Rec
        + VlAcresConf_Rec
    ) - (
          VlDescontoConf_Rec
        + ValDescontoImpostoConf_Rec
        + ValDescontoCondicionalConf_rec
    ))                                                              [ValorBaseCupom]
FROM Recebidas
WHERE CAST(Data_Rec AS DATE) >= @IniJulho
  AND CAST(Data_Rec AS DATE) <  @Corte
  AND CAST(DataCad_Rec AS DATE) >= @Corte
  AND Tipo_rec <> '1'
  AND LEFT(Obra_rec, 2) IN ('65','67','68','69')
GROUP BY CAST(DataCad_Rec AS DATE)
ORDER BY [DiaCadastro];

-- --------------------------------------------------------
-- 3) Monitor de completude: recebimentos por dia de pagamento no fim
-- do mes. Rodar 2x com intervalo; numeros iguais = base fechou e a
-- apuracao do fechamento pode rodar.
-- --------------------------------------------------------
SELECT
    CAST(Data_Rec AS DATE)                                          [DiaPagamento],
    COUNT(*)                                                        [QtdRecebimentos],
    SUM(ValorConf_Rec)                                              [ValorPrincipalConf]
FROM Recebidas
WHERE CAST(Data_Rec AS DATE) >= '20260728'
  AND CAST(Data_Rec AS DATE) <  @Corte
  AND LEFT(Obra_rec, 2) IN ('65','67','68','69')
GROUP BY CAST(Data_Rec AS DATE)
ORDER BY [DiaPagamento];

-- --------------------------------------------------------
-- 4) Amostra para conferencia manual no UAU (sem dados pessoais):
-- 20 baixas tardias mais recentes. Conferir no UAU que o pagamento
-- realmente ocorreu na Data_Rec e que a baixa foi processada depois.
-- --------------------------------------------------------
SELECT TOP 20
    Empresa_rec                                                     [Empresa],
    Obra_rec                                                        [Obra],
    NumVend_rec                                                     [Venda],
    NumParc_Rec                                                     [Parcela],
    Tipo_rec                                                        [TipoParcela],
    CAST(Data_Rec AS DATE)                                          [DataPagamento],
    CAST(DataCad_Rec AS DATE)                                       [DataCadastro]
FROM Recebidas
WHERE CAST(Data_Rec AS DATE) >= '20260730'
  AND CAST(Data_Rec AS DATE) <  @Corte
  AND CAST(DataCad_Rec AS DATE) >= @Corte
  AND LEFT(Obra_rec, 2) IN ('65','67','68','69')
ORDER BY DataCad_Rec DESC;
