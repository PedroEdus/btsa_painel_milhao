-- Fechamento retroativo Julho/2026 - Apuracao completa do Sorteio (v4)
-- v4 (11/08/2026): resgate de cessoes no de-para do snapshot. Cessao
--   aprovada (VendaHist.TipoMnt_vhist = 2) gera VENDA NOVA no nome do
--   cessionario (NumNovaVend_vhist); a antiga migra p/ VendasRecebidas
--   status 1 (cancelada). O universo v2 ja traz as duas pontas, mas sem
--   encadeamento o de-para snapshot x reexecucao quebrava (mecanismo dos
--   8 sem retorno de 06/08). Colunas novas:
--   - [Data Cessao] / [Cessao Apos Fechamento]: analogo ao Distrato Apos
--     Fechamento - cessao aprovada >= 01/08 significa que a venda ANTIGA
--     estava ativa em 31/07 e seus cupons de julho valem no fechamento.
--   - [Venda Nova Cessao]: de-para antiga -> nova (mesma empresa/obra).
--   - [Venda Origem Cessao]: de-para nova -> antiga.
--   Downstream junta as pontas por esse par; cupons NAO sao somados
--   entre pontas. DECISAO DE NEGOCIO 11/08/2026: cada dono tem o seu
--   cupom (cedente = gerados ANTES da cessao; cessionario = os da venda
--   nova); quitada na campanha segue concorrendo no sorteio final.
--   Por isso recJul corta recebimentos de venda cedida em Data_Rec <
--   data da cessao - no dia ou depois = suspeita de baixa tecnica
--   (media R$ 335k/venda; conferir com
--   sql/validacao_recebimentos_tecnicos_cessao.sql).
--   Validacao: sql/validacao_cessoes.sql + Resultados/validacao_cessoes.xlsx
--   (729 cessoes na campanha ate 10/08; 128 vendas novas ja quitadas).
-- v3 (10/08/2026 - DECISAO CONJUNTA em reuniao): cupom passa a ser gerado
--   sobre o VALOR RECEBIDO INTEGRAL (inclui multa, juros de atraso,
--   correcao de atraso e taxa de boleto), substituindo a regra anterior do
--   regulamento item 6.3 que excluia encargos. [Valor Gera Cupom Julho]
--   (regra antiga) permanece na saida como referencia de auditoria.
--   PENDENTE: 1) alinhar a geracao de cupons da API do site a mesma regua
--   (senao o de-para quebra); 2) validar com juridico/regulamento;
--   3) regerar a lista de julho ja apurada.
-- Contexto (reuniao de validacoes 04/08/2026): pagamentos de 30-31/07
--   (PIX/boleto) so foram baixados entre 01 e 06/08. O snapshot batido em
--   31/07 ficou incompleto. Como Data_Rec preserva a data REAL do
--   recebimento (a baixa tardia muda so a conciliacao, nao a data), a base
--   correta de julho e reconstruivel depois que as baixas terminarem.
-- v2 (06/08/2026): a v1 filtrava Status_Ven = 0 e excluia distratos via
--   NOT EXISTS - vendas que mudaram de status APOS o fechamento sumiam do
--   de-para com o snapshot (235 casos em julho). Agora a query traz TODAS
--   as vendas do universo (qualquer status, com ou sem distrato) e EXPOE
--   as informacoes de status/distrato em colunas, em vez de filtrar:
--   - [Status Venda]: 0 Normal, 1 Cancelada, 2 Alterada, 3 Quitada,
--     4 Em Acerto (3 e 4 observados nos dados, sem dicionario UAU).
--     Vendas quitadas/canceladas vivem em VendasRecebidas (a tabela Vendas
--     so tem status 0 - medicao vault 10/07).
--   - [Distrato Aprovado] + classificacao: ultimo distrato efetivo da
--     venda (TipoAditivo_vdd = 0, StatusAprov_vdd = 1), categoria parseada
--     de CategoriasDeDistrato (padrao TIPO - MOTIVO).
--   - [Classificacao Distrato]: CANCELAMENTO x TRANSFERENCIA. Sinal de
--     transferencia = cessao de direito aprovada em VendaHist
--     (TipoMnt_vhist = 2). Heuristica - validar com negocio.
--   - [Distrato Apos Fechamento]: 1 = distrato aprovado/gerado a partir de
--     01/08 (a venda ESTAVA ativa no fechamento de julho). E o caso dos
--     92 sumidos pendentes de decisao Carlos/Robson.
--   A elegibilidade final vira FILTRO downstream (ex.: status normal/
--   quitada, sem distrato ou distrato pos-fechamento, APTO, cupons > 0),
--   nao filtro embutido na query.
-- Regua de aptidao no fechamento (reg. 6.7): parcela vencida ate 31/07
--   ainda em aberto em 31/07 = NAO APTO. No fechamento a regua diaria e a
--   mensal coincidem (corte < 01/08). [Status Fechamento Julho] continua
--   olhando SO parcelas - status de venda/distrato NAO entram na regua.
-- Reconstrucao retroativa do status em 31/07 (2 fontes):
--   (a) parcela em ContasReceber com vencimento < 01/08 ainda aberta hoje
--       => estava aberta no fechamento. Resgate de baixa atrasada: se
--       existe recebimento da MESMA parcela com Data_Rec <= 31/07, a baixa
--       so atrasou - nao conta como aberta. (Pagamento parcial pode
--       mascarar parcela meio aberta - caso raro, mesma limitacao da
--       query principal.)
--   (b) parcela ja paga hoje, mas com Data_Rec >= 01/08 e vencimento ate
--       31/07 => estava vencida e em aberto no fechamento (quem pagou em
--       agosto nao vira apto de julho retroativamente).
-- Cupons Casas Julho = FLOOR(base de cupom com Data_Rec em julho / 100),
--   com CLAMP em zero (estorno liquido gerava cupom negativo - caso real
--   de julho: venda 5530/obra 69717, R$ -2,14 -> -1 cupom). Composicao
--   identica ao Valor Gera Cupom da query principal (sem multa, taxa de
--   boleto e encargos de atraso - regulamento 6.3).
-- NAO usar DataCad_Rec para detectar baixa atrasada: hipotese testada e
--   REFUTADA em 06/08/2026 (sql/validacao_datacad_rec.sql, bloco 1: 98,8%
--   das linhas tem DataCad_Rec < Data_Rec - a coluna nao e a data de
--   processamento da baixa). O de-para do que o snapshot de 31/07 nao viu
--   e feito comparando o snapshot com a reexecucao desta query.
-- RODAR na origem (BURITI-BD-02 via gateway), somente apos as baixas do
--   fechamento terminarem (monitor: bloco 3 de validacao_datacad_rec.sql).
-- Empresas de teste excluidas (mesma lista da query principal).
-- Autor: Pedro (04/08/2026; v2 em 06/08/2026)

DECLARE @IniJulho date = '20260701';
DECLARE @Corte    date = '20260801';   -- primeiro dia apos o fechamento

SELECT
    pc.Empresa_ven                                              [CodEmpresa],
    pc.Obra_Ven                                                 [CodObra],
    pc.Num_Ven                                                  [Venda],
    UPPER(pes.Nome_pes)                                         [NomeCliente],
    pes.cpf_pes                                                 [CPF],
    -- Regra antiga (reg. 6.3, sem encargos) - mantida como referencia
    ISNULL(recJul.ValorCupomJulho, 0)                           [Valor Gera Cupom Julho],

    -- Base OFICIAL do cupom desde 10/08/2026: valor recebido integral
    ISNULL(recJul.ValorRecebidoJulho, 0)                        [Valor Recebido Julho],

    -- Clamp em zero: estorno liquido nao gera cupom negativo
    IIF(ISNULL(recJul.ValorRecebidoJulho, 0) > 0,
        FLOOR(ISNULL(recJul.ValorRecebidoJulho, 0) / 100),
        0)                                                      [Cupons Casas Julho],

    FORMAT(recJul.UltimoRecebimentoJulho, 'dd/MM/yyyy')         [Ultimo Recebimento Julho],

    CASE
        WHEN abertas.NumVend_prc     IS NOT NULL
          OR pagasDepois.NumVend_Rec IS NOT NULL
            THEN 'NAO APTO'
        ELSE 'APTO'
    END                                                         [Status Fechamento Julho],

    CASE
        WHEN abertas.NumVend_prc     IS NOT NULL
          OR pagasDepois.NumVend_Rec IS NOT NULL
            THEN 'PARCELA VENCIDA EM ABERTO EM 31/07'
        ELSE 'ADIMPLENTE NO FECHAMENTO'
    END                                                         [Motivo],

    -- Diagnostico do de-para: 1 = teve pagamento nos dias 30-31/07
    CASE
        WHEN recJul.TevePgtoFimDeMes = 1 THEN 1
        ELSE 0
    END                                                         [Pgto 30-31/07],

    -- --------------------------------------------------------
    -- Situacao da venda (v2): exposta em colunas, nao filtrada
    -- --------------------------------------------------------
    pc.FonteVenda                                               [Fonte Venda],

    CASE pc.Status_Ven
        WHEN 0 THEN 'NORMAL'
        WHEN 1 THEN 'CANCELADA'
        WHEN 2 THEN 'ALTERADA'
        WHEN 3 THEN 'QUITADA'
        WHEN 4 THEN 'EM ACERTO'
        ELSE CONCAT('DESCONHECIDO (', pc.Status_Ven, ')')
    END                                                         [Status Venda],

    IIF(dist.NumVend_vdd IS NOT NULL, 'Sim', 'Nao')             [Distrato Aprovado],

    -- CANCELAMENTO x TRANSFERENCIA: cessao de direito aprovada em
    -- VendaHist (TipoMnt_vhist = 2) marca transferencia. Heuristica -
    -- conferir tambem [Categoria Distrato]/[Motivo Distrato].
    CASE
        WHEN dist.NumVend_vdd IS NULL     THEN ''
        WHEN hist.TeveCessao = 1          THEN 'TRANSFERENCIA (CESSAO DE DIREITO)'
        ELSE 'CANCELAMENTO'
    END                                                         [Classificacao Distrato],

    CASE dist.TipoDistrato_vdd
        WHEN 0 THEN 'NORMAL'
        WHEN 1 THEN 'ADMINISTRATIVO'
        ELSE ''
    END                                                         [Tipo Distrato],

    -- Desc_cd segue o padrao TIPO - MOTIVO (parsing padrao do vault)
    CASE
        WHEN cd.Desc_cd IS NULL THEN ''
        WHEN CHARINDEX(' - ', cd.Desc_cd) > 0
            THEN LTRIM(RTRIM(SUBSTRING(cd.Desc_cd, 1,
                 CHARINDEX(' - ', cd.Desc_cd) - 1)))
        ELSE LTRIM(RTRIM(cd.Desc_cd))
    END                                                         [Categoria Distrato],

    CASE
        WHEN cd.Desc_cd IS NULL THEN ''
        WHEN CHARINDEX(' - ', cd.Desc_cd) > 0
            THEN LTRIM(RTRIM(SUBSTRING(cd.Desc_cd,
                 CHARINDEX(' - ', cd.Desc_cd) + 3, LEN(cd.Desc_cd))))
        ELSE ''
    END                                                         [Motivo Distrato],

    FORMAT(dist.DataCad_vdd,   'dd/MM/yyyy')                    [Data Geracao Distrato],
    FORMAT(dist.DataAprov_vdd, 'dd/MM/yyyy')                    [Data Aprovacao Distrato],

    -- 1 = distrato aprovado/gerado a partir de 01/08: a venda estava
    -- ATIVA no fechamento de julho (pendencia dos 92 - decisao de negocio).
    -- DataAprov_vdd tem nulos mesmo em aprovados; fallback = DataCad_vdd.
    IIF(dist.NumVend_vdd IS NOT NULL
        AND CAST(COALESCE(dist.DataAprov_vdd, dist.DataCad_vdd) AS DATE) >= @Corte,
        1, 0)                                                   [Distrato Apos Fechamento],

    -- Flags brutas do historico de manutencao (VendaHist, aprovadas)
    IIF(hist.TeveCessao = 1,        'Sim', 'Nao')               [Cessao Hist],
    IIF(hist.TeveRenegociacao = 1,  'Sim', 'Nao')               [Renegociacao Hist],

    -- Cessao de direito (v4): encadeamento antiga <-> nova p/ o de-para
    FORMAT(cess.DataCessao, 'dd/MM/yyyy')                       [Data Cessao],

    -- 1 = cessao aprovada a partir de 01/08: a venda ANTIGA estava ativa
    -- no fechamento de julho (cupons de julho dela valem no snapshot)
    IIF(cess.NumVend_vhist IS NOT NULL
        AND CAST(cess.DataAprovacao AS DATE) >= @Corte, 1, 0)   [Cessao Apos Fechamento],

    cess.VendaNova                                              [Venda Nova Cessao],
    cessOrig.VendaOrigem                                        [Venda Origem Cessao]

FROM
(
    -- Vendas ativas + quitadas/canceladas, TODOS os status (v2).
    -- UNION ALL + ROW_NUMBER: venda presente nas duas tabelas (transicao)
    -- fica com a linha de Vendas (fonte viva).
    SELECT Empresa_ven, Obra_ven, Num_Ven, Status_ven, Cliente_Ven, FonteVenda
    FROM
    (
        SELECT
            u.*,
            ROW_NUMBER() OVER (
                PARTITION BY u.Empresa_ven, u.Obra_ven, u.Num_Ven
                ORDER BY u.OrdemFonte
            ) AS rn
        FROM
        (
            SELECT
                Empresa_ven, Obra_ven, Num_Ven, Status_ven, Cliente_Ven,
                'VENDAS' AS FonteVenda, 1 AS OrdemFonte
            FROM Vendas
            WHERE LEFT(Obra_ven, 2) IN ('65','67','68','69')

            UNION ALL

            SELECT
                Empresa_vrec, Obra_VRec, Num_VRec, Status_Vrec, Cliente_VRec,
                'VENDAS RECEBIDAS' AS FonteVenda, 2 AS OrdemFonte
            FROM VendasRecebidas
            WHERE LEFT(Obra_VRec, 2) IN ('65','67','68','69')
        ) AS u
    ) AS dedup
    WHERE dedup.rn = 1
) AS pc

LEFT JOIN Pessoas AS pes
    ON pes.cod_pes = pc.Cliente_Ven

-- --------------------------------------------------------
-- Recebimentos de julho (Data_Rec = data real do pagamento,
-- independente de quando a baixa foi processada)
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT
        r.Empresa_rec,
        r.Obra_rec,
        r.NumVend_rec,

        SUM((
              r.ValorConf_Rec
            + r.VlJurosParcConf_Rec
            + r.VlCorrecaoConf_Rec
            + r.VlAcresConf_Rec
        ) - (
              r.VlDescontoConf_Rec
            + r.ValDescontoImpostoConf_Rec
            + r.ValDescontoCondicionalConf_rec
        ))                              AS ValorCupomJulho,

        -- Valor recebido INTEGRAL (base oficial do cupom desde 10/08):
        -- inclui multa, juros de atraso, correcao de atraso e taxa de
        -- boleto; desconta todos os descontos, inclusive custas.
        SUM((
              r.ValorConf_Rec
            + r.VlJurosParcConf_Rec
            + r.VlCorrecaoConf_Rec
            + r.VlAcresConf_Rec
            + r.VlTaxaBolConf_Rec
            + r.VlMultaConf_Rec
            + r.VlJurosConf_Rec
            + r.VlCorrecaoAtrConf_Rec
        ) - (
              r.VlDescontoConf_Rec
            + r.ValDescontoCustaConf_Rec
            + r.ValDescontoImpostoConf_Rec
            + r.ValDescontoCondicionalConf_rec
        ))                              AS ValorRecebidoJulho,

        MAX(CASE
                WHEN CAST(r.Data_Rec AS DATE) >= '20260730'
                THEN 1
                ELSE 0
            END)                        AS TevePgtoFimDeMes,

        MAX(r.Data_Rec)                 AS UltimoRecebimentoJulho
    FROM Recebidas r
    -- Venda cedida: recebimento de julho so conta ate a VESPERA da
    -- cessao (no dia ou depois = suspeita de baixa tecnica, nao e
    -- pagamento do cedente) - decisao de negocio 11/08/2026.
    LEFT JOIN
    (
        SELECT Empresa_vhist, Obra_vhist, NumVend_vhist,
               MAX(DataMnt_vhist) AS DataCessao
        FROM VendaHist
        WHERE TipoMnt_vhist = 2
          AND DataAprovacao_vhist IS NOT NULL
          AND LEFT(Obra_vhist, 2) IN ('65','67','68','69')
        GROUP BY Empresa_vhist, Obra_vhist, NumVend_vhist
    ) AS ced
        ON  ced.Empresa_vhist = r.Empresa_rec
        AND ced.Obra_vhist    = r.Obra_rec
        AND ced.NumVend_vhist = r.NumVend_rec
    WHERE CAST(r.Data_Rec AS DATE) >= @IniJulho
      AND CAST(r.Data_Rec AS DATE) <  @Corte
      AND r.Tipo_rec <> '1'
      AND LEFT(r.Obra_rec, 2) IN ('65','67','68','69')
      AND (ced.DataCessao IS NULL
           OR CAST(r.Data_Rec AS DATE) < CAST(ced.DataCessao AS DATE))
    GROUP BY r.Empresa_rec, r.Obra_rec, r.NumVend_rec
) AS recJul
    ON  recJul.Empresa_rec = pc.Empresa_ven
    AND recJul.Obra_rec    = pc.Obra_Ven
    AND recJul.NumVend_rec = pc.Num_Ven

-- --------------------------------------------------------
-- (a) Parcela vencida ate 31/07 ainda em aberto hoje.
-- NOT EXISTS = resgate de baixa atrasada: recebimento da mesma
-- parcela com Data_Rec dentro de julho significa que o cliente
-- pagou no prazo e so a baixa demorou.
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT DISTINCT
        cr.Empresa_prc,
        cr.Obra_prc,
        cr.NumVend_prc
    FROM ContasReceber cr
    WHERE LEFT(cr.Obra_Prc, 2) IN ('65','67','68','69')
      AND cr.Data_Prc < @Corte
      AND NOT EXISTS (
            SELECT 1
            FROM Recebidas r
            WHERE r.Empresa_rec    = cr.Empresa_prc
              AND r.Obra_Rec       = cr.Obra_Prc
              AND r.NumVend_Rec    = cr.NumVend_prc
              AND r.NumParc_Rec    = cr.NumParc_Prc
              AND r.NumParcGer_Rec = cr.NumParcGer_Prc
              AND r.Tipo_Rec       = cr.Tipo_Prc
              AND CAST(r.Data_Rec AS DATE) < @Corte
      )
) AS abertas
    ON  abertas.Empresa_prc = pc.Empresa_ven
    AND abertas.Obra_prc    = pc.Obra_Ven
    AND abertas.NumVend_prc = pc.Num_Ven

-- --------------------------------------------------------
-- (b) Parcela vencida ate 31/07 paga so em agosto: no fechamento
-- estava vencida e em aberto => NAO APTO em julho.
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT DISTINCT
        r.Empresa_rec,
        r.Obra_Rec,
        r.NumVend_Rec
    FROM Recebidas r
    WHERE LEFT(r.Obra_rec, 2) IN ('65','67','68','69')
      AND CAST(r.DataVenci_Rec AS DATE) < @Corte
      AND CAST(r.Data_Rec     AS DATE) >= @Corte
) AS pagasDepois
    ON  pagasDepois.Empresa_rec = pc.Empresa_ven
    AND pagasDepois.Obra_Rec    = pc.Obra_Ven
    AND pagasDepois.NumVend_Rec = pc.Num_Ven

-- --------------------------------------------------------
-- Ultimo distrato EFETIVO e APROVADO da venda (v2: exposto, nao
-- filtrado). TipoAditivo_vdd = 0 (distrato, nao aditivo) e
-- StatusAprov_vdd = 1 (flag oficial - nao usar DataAprov_vdd como
-- proxy: ha aprovados com data nula). ROW_NUMBER evita a armadilha
-- de multiplicacao com 2+ distratos na mesma venda (vault).
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT
        d.Empresa_vdd,
        d.Obra_vdd,
        d.NumVend_vdd,
        d.TipoDistrato_vdd,
        d.CategDistrato_vdd,
        d.DataCad_vdd,
        d.DataAprov_vdd
    FROM
    (
        SELECT
            Empresa_vdd, Obra_vdd, NumVend_vdd, TipoDistrato_vdd,
            CategDistrato_vdd, DataCad_vdd, DataAprov_vdd,
            ROW_NUMBER() OVER (
                PARTITION BY Empresa_vdd, Obra_vdd, NumVend_vdd
                ORDER BY DataCad_vdd DESC, Num_vdd DESC
            ) AS rn
        FROM VendaDistrato
        WHERE TipoAditivo_vdd = 0
          AND StatusAprov_vdd = 1
    ) AS d
    WHERE d.rn = 1
) AS dist
    ON  dist.Empresa_vdd = pc.Empresa_ven
    AND dist.Obra_vdd    = pc.Obra_Ven
    AND dist.NumVend_vdd = pc.Num_Ven

LEFT JOIN CategoriasDeDistrato AS cd
    ON cd.Codigo_cd = dist.CategDistrato_vdd

-- --------------------------------------------------------
-- Historico de manutencao (VendaHist): distingue cessao de direito
-- (TipoMnt_vhist = 2 = transferencia) de cancelamento (0) e
-- renegociacao (1). So manutencoes aprovadas.
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT
        Empresa_vhist,
        Obra_vhist,
        NumVend_vhist,
        MAX(IIF(TipoMnt_vhist = 0 AND DataAprovacao_vhist IS NOT NULL, 1, 0)) AS TeveCancelamento,
        MAX(IIF(TipoMnt_vhist = 1 AND DataAprovacao_vhist IS NOT NULL, 1, 0)) AS TeveRenegociacao,
        MAX(IIF(TipoMnt_vhist = 2 AND DataAprovacao_vhist IS NOT NULL, 1, 0)) AS TeveCessao
    FROM VendaHist
    WHERE LEFT(Obra_vhist, 2) IN ('65','67','68','69')
    GROUP BY Empresa_vhist, Obra_vhist, NumVend_vhist
) AS hist
    ON  hist.Empresa_vhist = pc.Empresa_ven
    AND hist.Obra_vhist    = pc.Obra_Ven
    AND hist.NumVend_vhist = pc.Num_Ven

-- --------------------------------------------------------
-- Cessao (v4), lado da venda CEDIDA: ultima cessao aprovada desta
-- venda + numero da venda nova gerada (NumNovaVend_vhist).
-- ROW_NUMBER: venda com mais de uma manutencao fica com a cessao
-- mais recente (armadilha de multiplicacao do vault).
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT c.Empresa_vhist, c.Obra_vhist, c.NumVend_vhist,
           c.DataMnt_vhist        AS DataCessao,
           c.DataAprovacao_vhist  AS DataAprovacao,
           c.NumNovaVend_vhist    AS VendaNova
    FROM
    (
        SELECT Empresa_vhist, Obra_vhist, NumVend_vhist, DataMnt_vhist,
               DataAprovacao_vhist, NumNovaVend_vhist,
               ROW_NUMBER() OVER (
                   PARTITION BY Empresa_vhist, Obra_vhist, NumVend_vhist
                   ORDER BY DataAprovacao_vhist DESC, Num_vhist DESC
               ) AS rn
        FROM VendaHist
        WHERE TipoMnt_vhist = 2
          AND DataAprovacao_vhist IS NOT NULL
          AND LEFT(Obra_vhist, 2) IN ('65','67','68','69')
    ) AS c
    WHERE c.rn = 1
) AS cess
    ON  cess.Empresa_vhist = pc.Empresa_ven
    AND cess.Obra_vhist    = pc.Obra_Ven
    AND cess.NumVend_vhist = pc.Num_Ven

-- --------------------------------------------------------
-- Cessao (v4), lado da venda NOVA: de qual venda esta foi originada.
-- GROUP BY garante 1 linha por venda nova.
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT Empresa_vhist, Obra_vhist, NumNovaVend_vhist,
           MAX(NumVend_vhist) AS VendaOrigem
    FROM VendaHist
    WHERE TipoMnt_vhist = 2
      AND DataAprovacao_vhist IS NOT NULL
      AND NumNovaVend_vhist IS NOT NULL
      AND LEFT(Obra_vhist, 2) IN ('65','67','68','69')
    GROUP BY Empresa_vhist, Obra_vhist, NumNovaVend_vhist
) AS cessOrig
    ON  cessOrig.Empresa_vhist     = pc.Empresa_ven
    AND cessOrig.Obra_vhist        = pc.Obra_Ven
    AND cessOrig.NumNovaVend_vhist = pc.Num_Ven

WHERE pc.Empresa_ven NOT IN (3, 204, 226, 229, 301, 302)

ORDER BY [Status Venda], [Status Fechamento Julho], [NomeCliente];
