/*
-- Relatório de Sorteio - Campanha 5 Casas & 1 Milhão (Virada de Prêmios)
-- Período da campanha: 01/07/2026 a 31/12/2026
-- Cupom: R$ 100 pagos = 1 cupom. NÃO geram cupom: multa, taxa de boleto,
--   juros de atraso e correção de atraso (regulamento item 6.3).
-- Cupons Milhão: acumulado da campanha inteira (sorteio final 18/01/2027).
-- Cupons Casas: valor recebido no mês vigente / 100.
-- APTO: adimplente no encerramento do período (regulamento 6.7) = nenhuma
--   parcela vencida até o fim do mês anterior em aberto.
-- Inad Junho (data fixa 30/06): 1 = estava inadimplente na largada da campanha
--   (parcela vencida até 30/06 ainda aberta OU paga durante a campanha).
-- Inad Junho continua sendo o marcador de largada (30/06 fixo).
-- Valor Inadimplência: dívida vencida TOTAL (fórmula Carteira Migração).
-- Jurídico Ativo/Passivo: ocorrência jurídica vinculada à venda
--   (OcorrenciaVinculo, NumOco_ocv 4=Ativo / 32=Passivo, Status_ocv=0 aberta).
-- Antecipação: pagamento recebido em mês ANTERIOR ao mês de vencimento
--   da parcela (EOMONTH(Data_Rec) < EOMONTH(DataVenci_Rec)). Granularidade
--   mensal, igual à régua de adimplência. Independente de Recuperação/APTO —
--   cliente pode antecipar parcela futura e continuar inadimplente/inapto.
-- Recuperação: pagamento recebido DEPOIS da data de vencimento da parcela
--   (Data_Rec > DataVenci_Rec, granularidade diária) = quitou parcela que
--   já estava vencida.
--   Pagamento no próprio dia do vencimento ou antes (mesmo mês) = normal.
-- Valor Juros/Multa Inadimplência: decomposição do Valor Inadimplência
--   (ValJuroAtraso_crc / ValMultaAtraso_crc, ContasReceberCalc), mesmo
--   filtro/universo do Valor Inadimplência total (inclui Tipo '1').
-- Valor Antecipado: soma dos recebimentos da campanha pagos antes do
--   vencimento da própria parcela.
-- Empresas excluídas: 3, 204, 226, 229, 301, 302
-- Distrato: Status_Ven = 0 (Normal) é o filtro principal; NOT EXISTS em
--   VendaDistrato fica como redundância/segurança (distrato com status
--   ainda não refletido). Só distrato efetivo (TipoAditivo_vdd = 0, sem
--   aditivo) e aprovado (StatusAprov_vdd = 1 — flag oficial do UAU).
--   Tentativa de Status_Ven IN (0,1,3) revertida 08/07/2026 — trazia
--   23 anos de histórico (234k linhas).
-- Fonte de valores de parcela: CONTROLADORIA.dbo.ContasReceberCalc_bkp
--   (snapshot do job noturno, mesma fonte do BI Carteira Migração).
--   Decisão 10/07: a viva do UAU ficou ~1 dia com valores quebrados em
--   09/07 (instabilidade); _bkp é mais estável (pior caso = D-1).
--   Requer execução na origem (gateway) — espelho não tem CONTROLADORIA.
--   Painel deve alertar queda >20% de inad entre janelas mesmo assim.
-- Autor: Carlos Eduardo
-- Última atualização: 10/07/2026 (Pedro — Jurídico Ativo/Passivo,
--   Antecipação mensal + Recuperação diária com valores, Juros/Multa
--   Inadimplência, exclusão Distrato com TipoAditivo/StatusAprov)
*/

SELECT
    pc.Cidade                                                   [Cidade],
    REPLACE(pc.Regional, 'REGIONAL', '')                        [Regional],
    pc.Empresa_ven                                              [CodEmpresa],
    pc.Obra_Ven                                                 [CodObra],
    pc.descr_obr                                                [NomeObra],
    pc.Desc_emp                                                 [NomeEmpresa],
    ps.Descricao_psc                                            [Produto],
    pc.Num_Ven                                                  [Venda],
    up.identificador_unid                                       [Identificador],
    FORMAT(pc.Data_Ven, 'dd/MM/yyyy')                           [Dt.Venda],
    FORMAT(pc.ValorTot_Ven, 'C')                                [VlrVenda],
    UPPER(PesCli.Nome_pes)                                      [NomeCliente],
    PesCli.cpf_pes,
    LOWER(PesCli.Email_pes)                                     [EmailCliente],
    TelefoneFormatado,
    TipoTelefone,

    CASE
        WHEN crConsolidado.StatusContasReceber = 'Inadimplente' THEN 'Inadimplente'
        ELSE 'Adimplente'
    END                                                         [StatuVenda],

    -- Flag: estava inadimplente em 30/06 (largada da campanha)? 1 = sim
    CASE
        WHEN crConsolidado.ParcelaAbertaAntesJulho = 1
          OR recTotais.PagouVencidaAntesJulho = 1
            THEN 1
        ELSE 0
    END                                                         [Inad Junho],

    -- Flag: pagou na campanha parcela DEPOIS do vencimento? 1 = recuperação
    CASE
        WHEN recTotais.Recuperou = 1 THEN 1
        ELSE 0
    END                                                         [Recuperação],

    -- Valor recebido de parcelas pagas após a data de vencimento (diário)
    FORMAT(ISNULL(recTotais.ValorRecuperado, 0), 'C')           [Valor Recuperado],

    -- Flag: pagou parcela com vencimento em mês futuro? Independe de
    -- Recuperação/APTO — antecipar não quita parcela vencida anterior.
    CASE
        WHEN recTotais.Antecipou = 1 THEN 'Sim'
        ELSE 'Não'
    END                                                         [Antecipação],

    -- Valor recebido de parcelas com vencimento em mês futuro (campanha)
    FORMAT(ISNULL(recTotais.ValorAntecipado, 0), 'C')           [Valor Antecipado],

    -- Quantidade por tipo de parcela
    crConsolidado.Qtd_P                                         [Qtd Parcelas],
    crConsolidado.Qtd_S                                         [Qtd Sinal],
    crConsolidado.Qtd_SA                                        [Qtd Sinal/Arras],
    crConsolidado.Qtd_SN                                        [Qtd Sinal Negoci],
    crConsolidado.Qtd_E                                         [Qtd Entrada],
    crConsolidado.Qtd_ER                                        [Qtd Ent.Reativacao],
    crConsolidado.Qtd_AM                                        [Qtd Amortizacao],
    crConsolidado.Qtd_FC                                        [Qtd Financ.CEF],
    crConsolidado.Qtd_B                                         [Qtd Balao],
    crConsolidado.Qtd_R                                         [Qtd Residuo],
    crConsolidado.Qtd_I                                         [Qtd Intermediacao],
    crConsolidado.Qtd_OP                                        [Qtd Operacao XPI],

    -- Valores gerais
    FORMAT(ISNULL(crConsolidado.ValorAReceber,     0), 'C')     [Valor a Receber],
    FORMAT(ISNULL(crConsolidado.ValorInadimplente, 0), 'C')     [Valor Inadimplência],
    FORMAT(ISNULL(crConsolidado.ValorJurosInadimplencia, 0), 'C') [Valor Juros Inadimplência],
    FORMAT(ISNULL(crConsolidado.ValorMultaInadimplencia, 0), 'C') [Valor Multa Inadimplência],
    FORMAT(ISNULL(recTotais.ValorRec,              0), 'C')     [Valor Recebido],
    FORMAT(ISNULL(recTotais.ValorCupom,            0), 'C')     [Valor Gera Cupom],
    FORMAT(ISNULL(recTotais.ValorCupomMesAtual,    0), 'C')     [Valor Cupom Mês Atual],
    FORMAT(recTotais.DataUltimoRecebimento, 'dd/MM/yyyy')       [Data Último Recebimento],

    -- Cupons: sorteio do Milhão (acumulado da campanha)
    FLOOR(ISNULL(recTotais.ValorCupom, 0) / 100)                [Cupons Milhão],

    -- Cupons: sorteio das Casas (recebimentos do mês vigente)
    FLOOR(ISNULL(recTotais.ValorCupomMesAtual, 0) / 100)        [Cupons Casas],

    -- Diagnóstico: pagou a parcela do mês anterior?
    CASE
        WHEN parcMesAnt.ParcelaMesPassadoAberta = 1 THEN 'Não'
        ELSE 'Sim'
    END                                                         [Pagou Parcela Mês Anterior],
    DiasAtraso,

    -- Status final do sorteio (Apto / Não Apto)
    CASE
        WHEN crConsolidado.StatusContasReceber = 'Inadimplente'
            THEN 'NÃO APTO'
        ELSE 'APTO'
    END                                                         [Status Sorteio],

    -- Motivo do status do sorteio
    CASE
        WHEN crConsolidado.StatusContasReceber = 'Inadimplente'
            THEN 'PARCELA VENCIDA NO ENCERRAMENTO DO PERÍODO'
        ELSE 'ADIMPLENTE'
    END                                                         [Motivo],

    -- Ocorrência jurídica vinculada à venda (Ativo/Passivo)
    CASE WHEN ocor.JuridicoAtivo   = 1 THEN 'Sim' ELSE 'Não' END [Jurídico Ativo],
    CASE WHEN ocor.JuridicoPassivo = 1 THEN 'Sim' ELSE 'Não' END [Jurídico Passivo]

FROM
(
    -- Base de vendas ativas (Vendas + VendasRecebidas)
    SELECT
        ISNULL(grpCidade.desc_cger, UPPER(o.cid_obr))  AS Cidade,
        grpRegional.desc_cger                           AS Regional,
        v.Empresa_ven,
        v.Obra_Ven,
        v.Num_Ven,
        v.Data_Ven,
        ValorTot_Ven,
        v.Status_Ven,
        ValorTot_Ven                                    AS Faturamento,
        o.descr_obr,
        e.Desc_emp,
        v.Cliente_Ven
    FROM
    (
        SELECT
            Empresa_ven, Obra_ven, Num_Ven, Data_Ven, DataCad_Ven, Status_ven,
            Cliente_Ven,
            ValorTot_Ven + Acrescimo_Ven - Desconto_Ven AS ValorTot_Ven
        FROM Vendas
        WHERE  LEFT(Obra_ven, 2) IN ('65','67','68','69')

        UNION

        SELECT
            Empresa_vrec, Obra_VRec, Num_VRec, Data_VRec, DataCad_Vrec, Status_Vrec,
            Cliente_VRec,
            ValorTot_VRec + Acrescimo_VRec - Desconto_VRec AS ValorTot_VRec
        FROM VendasRecebidas
        WHERE LEFT(Obra_VRec, 2) IN ('65','67','68','69')

    ) AS v

    INNER JOIN Obras o
        ON  o.Empresa_obr = v.Empresa_ven
        AND o.cod_obr     = v.Obra_Ven

    INNER JOIN Empresas e
        ON  e.Codigo_emp  = o.Empresa_obr

    -- Subgrupo filho da obra (nó direto, qualquer LEN)
    LEFT JOIN GruposDeObra AS grpFilho
        ON  grpFilho.Codigo_cger = o.CodGrupo_obr

    -- Cidade: pai do subgrupo (7 primeiros chars do código filho)
    LEFT JOIN GruposDeObra AS grpCidade
        ON  grpCidade.Codigo_cger = LEFT(grpFilho.Codigo_cger, 7)

    -- Regional: avô do subgrupo (3 primeiros chars do código filho)
    LEFT JOIN GruposDeObra AS grpRegional
        ON  grpRegional.Codigo_cger = LEFT(grpFilho.Codigo_cger, 3)

    GROUP BY
        grpCidade.desc_cger,
        grpRegional.desc_cger,
        o.cid_obr,
        v.Empresa_ven, v.Obra_Ven, v.Num_Ven,
        v.Data_Ven, ValorTot_Ven, v.Status_Ven,
        o.descr_obr, e.Desc_emp, v.Cliente_Ven

) AS pc

-- --------------------------------------------------------
-- INNER JOIN: Itens da venda
-- ROW_NUMBER garante 1 linha por venda independente da fonte.
-- ItensRecebidas só entra via anti-join se não houver registro em ItensVenda.
-- --------------------------------------------------------
INNER JOIN
(
    SELECT Empresa_itv, Obra_itv, NumVend_Itv, Produto_itv, CodPerson_itv
    FROM
    (
        SELECT
            Empresa_itv, Obra_itv, NumVend_Itv, Produto_itv, CodPerson_itv,
            ROW_NUMBER() OVER (
                PARTITION BY Empresa_itv, Obra_itv, NumVend_Itv
                ORDER BY (SELECT NULL)
            ) AS rn
        FROM ItensVenda
    ) AS iv
    WHERE iv.rn = 1

    UNION ALL

    SELECT Empresa_itr, Obra_itr, NumVend_itr, Produto_itr, CodPerson_itr
    FROM
    (
        SELECT
            Empresa_itr, Obra_itr, NumVend_itr, Produto_itr, CodPerson_itr,
            ROW_NUMBER() OVER (
                PARTITION BY Empresa_itr, Obra_itr, NumVend_itr
                ORDER BY (SELECT NULL)
            ) AS rn
        FROM ItensRecebidas ir
        WHERE NOT EXISTS (
            SELECT 1 FROM ItensVenda iv2
            WHERE iv2.Empresa_itv = ir.Empresa_itr
              AND iv2.Obra_itv    = ir.Obra_itr
              AND iv2.NumVend_Itv = ir.NumVend_itr
        )
    ) AS ir2
    WHERE ir2.rn = 1
) AS itv
    ON  itv.Empresa_itv = pc.Empresa_ven
    AND itv.Obra_itv    = pc.Obra_Ven
    AND itv.NumVend_Itv = pc.Num_Ven


-- LEFT JOIN: Unidade/Personalização

LEFT JOIN
(
    SELECT Empresa_unid, Obra_unid, Prod_unid, NumPer_unid, identificador_unid
    FROM UnidadePer
    WHERE Vendido_unid <> 10 AND  LEFT(Obra_unid, 2) IN ('65','67','68','69')
) AS up
    ON  up.Empresa_unid = itv.Empresa_itv
    AND up.Obra_unid    = itv.Obra_itv
    AND up.Prod_unid    = itv.Produto_itv
    AND up.Numper_unid  = itv.CodPerson_itv


-- LEFT JOIN: Nome do Produto

LEFT JOIN PrdSrv AS ps
    ON ps.NumProd_psc = up.Prod_unid
    AND Status_psc = 1


-- LEFT JOIN: Cliente

LEFT JOIN Pessoas AS PesCli
    ON PesCli.cod_pes = pc.Cliente_Ven


-- LEFT JOIN: Melhor telefone por pessoa

LEFT JOIN
(
    SELECT
        classificado.pes_tel,
        classificado.NumeroTratado  AS TelefoneFormatado,
        classificado.TipoTel        AS TipoTelefone
    FROM
    (
        SELECT
            base.pes_tel,
            base.NumeroCompleto,
            base.FoneLimpo,

            CASE
                WHEN LEN(base.NumeroCompleto) = 11 AND LEFT(base.FoneLimpo, 1) = '9'
                    THEN base.NumeroCompleto
                WHEN LEN(base.NumeroCompleto) = 10 AND LEFT(base.FoneLimpo, 1) IN ('6','7','8','9')
                    THEN base.DddLimpo + '9' + base.FoneLimpo
                WHEN LEN(base.NumeroCompleto) = 10 AND LEFT(base.FoneLimpo, 1) IN ('2','3','4','5')
                    THEN base.NumeroCompleto
                ELSE base.NumeroCompleto
            END AS NumeroTratado,

            CASE
                WHEN LEN(base.NumeroCompleto) = 11 AND LEFT(base.FoneLimpo, 1) = '9'
                    THEN 'Celular'
                WHEN LEN(base.NumeroCompleto) = 10 AND LEFT(base.FoneLimpo, 1) IN ('6','7','8','9')
                    THEN 'Celular (corrigido)'
                WHEN LEN(base.NumeroCompleto) = 10 AND LEFT(base.FoneLimpo, 1) IN ('2','3','4','5')
                    THEN 'Fixo'
                ELSE 'Indefinido'
            END AS TipoTel,

            ROW_NUMBER() OVER (
                PARTITION BY base.pes_tel
                ORDER BY
                    CASE
                        WHEN LEN(base.NumeroCompleto) = 11 AND LEFT(base.FoneLimpo, 1) = '9'
                            THEN 1
                        WHEN LEN(base.NumeroCompleto) = 10 AND LEFT(base.FoneLimpo, 1) IN ('6','7','8','9')
                            THEN 2
                        WHEN LEN(base.NumeroCompleto) = 10 AND LEFT(base.FoneLimpo, 1) IN ('2','3','4','5')
                            THEN 3
                        ELSE 4
                    END
            ) AS prioridade

        FROM
        (
            SELECT
                pt.pes_tel,
                SUBSTRING(
                    REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(pt.ddd_tel)), '-',''),' ',''),'(',''),')',''),
                    PATINDEX('%[1-9]%', REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(pt.ddd_tel)), '-',''),' ',''),'(',''),')','') + '1'),
                    LEN(REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(pt.ddd_tel)), '-',''),' ',''),'(',''),')',''))
                ) AS DddLimpo,
                SUBSTRING(
                    REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(pt.fone_tel)), '-',''),' ',''),'(',''),')',''),
                    PATINDEX('%[1-9]%', REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(pt.fone_tel)), '-',''),' ',''),'(',''),')','') + '1'),
                    LEN(REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(pt.fone_tel)), '-',''),' ',''),'(',''),')',''))
                ) AS FoneLimpo
            FROM PesTel AS pt
        ) AS base0
        CROSS APPLY (
            SELECT  base0.pes_tel,
                    base0.DddLimpo,
                    base0.FoneLimpo,
                    base0.DddLimpo + base0.FoneLimpo AS NumeroCompleto
        ) AS base

    ) AS classificado
    WHERE classificado.prioridade = 1

) AS tel
    ON tel.pes_tel = pc.Cliente_Ven


-- --------------------------------------------------------
-- LEFT JOIN: Ocorrência jurídica vinculada à venda (Ativo/Passivo)
-- Join direto na venda (empresa + chave concatenada), sem passar por
-- item/unidade. NumOco_ocv: 4 = Jurídico Ativo, 32 = Jurídico Passivo.
-- Status_ocv = 0 -> ocorrência aberta.
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT
        Empresa_ocv,
        NumDoc_ocv,
        SUM(CASE WHEN NumOco_ocv = 4  THEN 1 ELSE 0 END) AS JuridicoAtivo,
        SUM(CASE WHEN NumOco_ocv = 32 THEN 1 ELSE 0 END) AS JuridicoPassivo
    FROM OcorrenciaVinculo
    WHERE Status_ocv = 0
      AND NumOco_ocv IN (4, 32)
    GROUP BY NumDoc_ocv, Empresa_ocv
) AS ocor
    ON  ocor.Empresa_ocv = pc.Empresa_ven
    AND ocor.NumDoc_ocv  = CONCAT('VENDAS ', pc.Num_Ven, '-', pc.Obra_Ven)


-- --------------------------------------------------------
-- LEFT JOIN: ContasReceber consolidado
-- StatusContasReceber: parcela vencida até o fim do mês anterior em aberto
--   (régua rolante: StatuVenda e Status Sorteio).
-- ParcelaAbertaAntesJulho: parcela vencida até 30/06 ainda em aberto
--   (data FIXA: base do flag Inad Junho).
-- ValorInadimplente = dívida vencida TOTAL (fórmula Carteira Migração),
--   inclui Tipo '1'.
-- ValorJurosInadimplencia / ValorMultaInadimplencia: decomposição do
--   Valor Inadimplência (mesmo filtro de parcela vencida).
-- --------------------------------------------------------
LEFT JOIN
(
    SELECT
        cr.Empresa_prc,
        cr.Obra_prc,
        cr.NumVend_prc,

        SUM(IIF(cr.Tipo_Prc = 'P',  1, 0))   AS Qtd_P,
        SUM(IIF(cr.Tipo_Prc = 'S',  1, 0))   AS Qtd_S,
        SUM(IIF(cr.Tipo_Prc = 'SA', 1, 0))   AS Qtd_SA,
        SUM(IIF(cr.Tipo_Prc = 'SN', 1, 0))   AS Qtd_SN,
        SUM(IIF(cr.Tipo_Prc = 'E',  1, 0))   AS Qtd_E,
        SUM(IIF(cr.Tipo_Prc = 'ER', 1, 0))   AS Qtd_ER,
        SUM(IIF(cr.Tipo_Prc = 'AM', 1, 0))   AS Qtd_AM,
        SUM(IIF(cr.Tipo_Prc = 'FC', 1, 0))   AS Qtd_FC,
        SUM(IIF(cr.Tipo_Prc = 'B',  1, 0))   AS Qtd_B,
        SUM(IIF(cr.Tipo_Prc = 'R',  1, 0))   AS Qtd_R,
        SUM(IIF(cr.Tipo_Prc = 'I',  1, 0))   AS Qtd_I,
        SUM(IIF(cr.Tipo_Prc = 'OP', 1, 0))   AS Qtd_OP,

        SUM(IIF(cr.Tipo_Prc <> '1', crc.ValParcela_crc, 0))   AS ValorAReceber,

        -- Vencida até o fim do mês anterior (rolante - reg. 6.7)
        MAX(
            CASE
                WHEN cr.Data_Prc < DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)
                    THEN 'Inadimplente'
            END
        )                                     AS StatusContasReceber,

        -- Vencida até 30/06 ainda em aberto (data fixa - flag Inad Junho)
        MAX(
            CASE
                WHEN cr.Data_Prc < '20260701'
                    THEN 1
            END
        )                                     AS ParcelaAbertaAntesJulho,

        DATEDIFF(DAY,
            MIN(
                CASE
                    WHEN cr.Data_Prc < DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)
                        THEN cr.Data_Prc
                END
            ),
            CAST(GETDATE() AS DATE)
        )                                     AS DiasAtraso,

        SUM(
            CASE
                WHEN cr.Data_Prc < CAST(GETDATE() AS DATE)
                    THEN ISNULL(crc.ValPrincipal_crc, 0)
                       + ISNULL(crc.ValJurosComp_crc, 0)
                       + ISNULL(crc.ValCorrecao_crc, 0)
                ELSE 0
            END
        )                                     AS ValorInadimplente,

        SUM(
            CASE
                WHEN cr.Data_Prc < CAST(GETDATE() AS DATE)
                    THEN ISNULL(crc.ValJuroAtraso_crc, 0)
                ELSE 0
            END
        )                                     AS ValorJurosInadimplencia,

        SUM(
            CASE
                WHEN cr.Data_Prc < CAST(GETDATE() AS DATE)
                    THEN ISNULL(crc.ValMultaAtraso_crc, 0)
                ELSE 0
            END
        )                                     AS ValorMultaInadimplencia

    FROM ContasReceber cr
    -- ContasReceberCalc_bkp (banco CONTROLADORIA, mesmo servidor): snapshot
    -- recalculado por job noturno — mesma fonte do BI Carteira Migração.
    -- Decisão 10/07 (2ª): a ContasReceberCalc viva do UAU ficou ~1 dia
    -- desatualizada em 09/07 (inad 62M vs 201M) por instabilidade do banco;
    -- a _bkp degrada no pior caso pra D-1, nunca pra valor quebrado.
    -- ATENÇÃO: cross-database — a query PRECISA rodar na origem
    -- (BURITI-BD-02 via gateway); no espelho Fabric CONTROLADORIA não existe.
    LEFT JOIN CONTROLADORIA.dbo.ContasReceberCalc_bkp crc
        ON  crc.Empresa_crc    = cr.Empresa_prc
        AND crc.Obra_crc       = cr.Obra_Prc
        AND crc.NumVend_crc    = cr.NumVend_prc
        AND crc.NumParc_crc    = cr.NumParc_Prc
        AND crc.NumParcGer_crc = cr.NumParcGer_Prc
        AND crc.Tipo_crc       = cr.Tipo_Prc
    WHERE LEFT(cr.Obra_Prc, 2) IN ('65','67','68','69')
    GROUP BY cr.Empresa_prc, cr.Obra_prc, cr.NumVend_prc

) AS crConsolidado
    ON  crConsolidado.Empresa_prc = pc.Empresa_ven
    AND crConsolidado.Obra_prc    = pc.Obra_Ven
    AND crConsolidado.NumVend_prc = pc.Num_Ven


-- --------------------------------------------------------
-- LEFT JOIN: Valores recebidos na campanha (01/07/2026 a 31/12/2026)
-- ValorRec               = total recebido (todos os componentes)
-- ValorCupom             = base de cupom (sem multa, taxa de boleto e
--                          encargos de atraso) -> Cupons Milhão
-- ValorCupomMesAtual     = base de cupom do mês vigente -> Cupons Casas
-- PagouVencidaAntesJulho = 1 se pagou na campanha parcela com vencimento
--                          até 30/06 (base do flag Inad Junho)
-- Antecipou/ValorAntecipado = pagamento de parcela com vencimento em mês
--                          POSTERIOR ao mês do recebimento (granularidade
--                          mensal). Não quita parcela vencida anterior.
-- Recuperou/ValorRecuperado = pagamento feito DEPOIS da data de vencimento
--                          da parcela (diário) = quitação de parcela
--                          já vencida.
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
            + r.VlTaxaBolConf_Rec
            + r.VlMultaConf_Rec
            + r.VlJurosConf_Rec
            + r.VlCorrecaoAtrConf_Rec
        ) - (
              r.VlDescontoConf_Rec
            + r.ValDescontoCustaConf_Rec
            + r.ValDescontoImpostoConf_Rec
            + r.ValDescontoCondicionalConf_rec
        ))                              AS ValorRec,

        SUM((
              r.ValorConf_Rec
            + r.VlJurosParcConf_Rec
            + r.VlCorrecaoConf_Rec
            + r.VlAcresConf_Rec
        ) - (
              r.VlDescontoConf_Rec
            + r.ValDescontoImpostoConf_Rec
            + r.ValDescontoCondicionalConf_rec
        ))                              AS ValorCupom,

        SUM(CASE
                WHEN CAST(r.Data_Rec AS DATE) >= DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)
                THEN (
                      r.ValorConf_Rec
                    + r.VlJurosParcConf_Rec
                    + r.VlCorrecaoConf_Rec
                    + r.VlAcresConf_Rec
                ) - (
                      r.VlDescontoConf_Rec
                    + r.ValDescontoImpostoConf_Rec
                    + r.ValDescontoCondicionalConf_rec
                )
                ELSE 0
            END)                        AS ValorCupomMesAtual,

        MAX(CASE
                WHEN CAST(r.DataVenci_Rec AS DATE) < '20260701'
                THEN 1
                ELSE 0
            END)                        AS PagouVencidaAntesJulho,

        MAX(CASE
                WHEN EOMONTH(r.Data_Rec) < EOMONTH(r.DataVenci_Rec)
                THEN 1
                ELSE 0
            END)                        AS Antecipou,

        SUM(CASE
                WHEN EOMONTH(r.Data_Rec) < EOMONTH(r.DataVenci_Rec)
                THEN (
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
                )
                ELSE 0
            END)                        AS ValorAntecipado,

        MAX(CASE
                WHEN CAST(r.Data_Rec AS DATE) > CAST(r.DataVenci_Rec AS DATE)
                THEN 1
                ELSE 0
            END)                        AS Recuperou,

        SUM(CASE
                WHEN CAST(r.Data_Rec AS DATE) > CAST(r.DataVenci_Rec AS DATE)
                THEN (
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
                )
                ELSE 0
            END)                        AS ValorRecuperado,

        MAX(r.Data_Rec)                 AS DataUltimoRecebimento
    FROM Recebidas r
    WHERE CAST(r.Data_Rec AS DATE) >= '20260701'
      AND CAST(r.Data_Rec AS DATE) <  '20270101'
      AND r.Tipo_rec <> '1'
      AND LEFT(r.Obra_rec, 2) IN ('65','67','68','69')
    GROUP BY r.Empresa_rec, r.Obra_rec, r.NumVend_rec

) AS recTotais
    ON  recTotais.Empresa_rec = pc.Empresa_ven
    AND recTotais.Obra_rec    = pc.Obra_Ven
    AND recTotais.NumVend_rec = pc.Num_Ven


-- LEFT JOIN: Tem parcela do mês passado em aberto? (diagnóstico)

LEFT JOIN
(
    SELECT DISTINCT
        cr.Empresa_prc,
        cr.Obra_prc,
        cr.NumVend_prc,
        1 AS ParcelaMesPassadoAberta
    FROM ContasReceber cr
    WHERE cr.Tipo_Prc <> '1'
      AND LEFT(cr.Obra_Prc, 2) IN ('65','67','68','69')
      AND cr.Data_Prc >= DATEADD(MONTH, -1, DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1))
      AND cr.Data_Prc <  DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)
) AS parcMesAnt
    ON  parcMesAnt.Empresa_prc = pc.Empresa_ven
    AND parcMesAnt.Obra_prc    = pc.Obra_Ven
    AND parcMesAnt.NumVend_prc = pc.Num_Ven

WHERE pc.Status_Ven = 0
  AND pc.Empresa_ven NOT IN (3, 204, 226, 229, 301, 302)

  -- Exclusão de distrato: só distrato efetivo (não aditivo) e aprovado.
  -- TipoAditivo_vdd: 0 = Distrato, 1 = Aditivo (dicionário UAU).
  -- StatusAprov_vdd: 0 = Não aprovado, 1 = Aprovado (flag oficial; existem
  -- aprovados com DataAprov_vdd nula, então não usar a data como filtro).
  AND NOT EXISTS (
        SELECT 1
        FROM VendaDistrato vdd
        WHERE vdd.Empresa_vdd      = pc.Empresa_ven
          AND vdd.obra_vdd         = pc.Obra_Ven
          AND vdd.NumVend_vdd      = pc.Num_Ven
          AND vdd.TipoAditivo_vdd  = 0
          AND vdd.StatusAprov_vdd  = 1
  )

ORDER BY pc.Cidade, pc.Regional, pc.Obra_Ven;
