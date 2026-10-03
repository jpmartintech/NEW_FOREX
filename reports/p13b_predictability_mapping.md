# P13B — Historical Predictability Mapping

Protocol: `p13b-historical-predictability-v1`
Config SHA256: `df417d2ffe1c664046de9c748a05a20033f77937c8ea080ed16a31ddd2a9c681`
Input census SHA256: `4281610c8fa4482b6de29da4efcb436e7eed1ea5c264c5ca3d8f24ae5b70569c`

## Auditoría

Se reutilizaron 2,400,000 filas válidas de P13/P13A. Se excluyó la corrida inválida de 99.000 evaluaciones; no se leyó el holdout. X contiene únicamente variables históricas archivadas y Y únicamente resultados forward.

## Variables

Variables históricas no disponibles y no reconstruidas: win rate, payoff ratio, frecuencia histórica, firma conductual histórica, coste histórico por operación y número de predicados.

## Resultados

variable,interval,generator,median_lift_E,positive_months,median_net_expectancy_R,median_net_return
complexity_interval,complexity_Q1,ga,1.029947411595444,7,-0.08073852901319295,-0.009061835112112199
complexity_interval,complexity_Q1,random,0.906311151026102,5,-0.0677399860723874,-0.010034816390557588
complexity_interval,complexity_Q2,ga,1.1950663099774237,9,-0.06807894279672135,-0.0045589848059659766
complexity_interval,complexity_Q2,random,1.058799433023513,10,-0.03987906114431761,-0.003022845218808856
complexity_interval,complexity_Q3,ga,1.1264579355587554,8,-0.019608186226366425,-0.0005399940236479606
complexity_interval,complexity_Q3,random,1.094670513546143,7,0.0,0.0
complexity_interval,complexity_Q4,ga,0.9285517468657157,3,0.0,0.0
complexity_interval,complexity_Q4,random,0.9997859179148071,4,0.0,0.0
complexity_interval,complexity_Q5,ga,0.7560020904474204,0,0.0,0.0
complexity_interval,complexity_Q5,random,0.8699095178045286,1,0.0,0.0
direction_interval,LONG,ga,1.0095667030183124,8,-0.012687235870942939,-0.000730731199108603
direction_interval,LONG,random,0.9914519375471168,5,-0.02639731549702196,-0.0018988694168969034
direction_interval,SHORT,ga,0.9303600104319336,4,-0.0335649371034247,-0.0020350176122167496
direction_interval,SHORT,random,1.0085244540070653,7,-0.02528074730339508,-0.001803903003730234
pf_interval,1.00–<1.10,ga,1.260806631232891,8,-0.11200053359094628,-0.009522488946713592
pf_interval,1.00–<1.10,random,1.1078923917221504,7,-0.07563776010719096,-0.006138989465826167
pf_interval,1.10–<1.20,ga,1.3069298660092727,10,-0.11073840229272731,-0.0077676264117787774
pf_interval,1.10–<1.20,random,1.2405256026659233,8,-0.07116669722293142,-0.004465064112668865
pf_interval,1.20–<1.30,ga,1.315320173301009,11,-0.10427179253776811,-0.006207160277378693
pf_interval,1.20–<1.30,random,1.410905977757368,7,-0.053457731679566134,-0.0027331946560070763
pf_interval,1.30–<1.50,ga,1.4139942578607818,12,-0.11396939046463192,-0.005625353727919558
pf_interval,1.30–<1.50,random,1.597028091529924,12,-0.02843084404072931,-0.0010856229024742425
pf_interval,PF < 1.00,ga,0.7626329353024266,2,0.0,0.0
pf_interval,PF < 1.00,random,0.9015794699200953,4,0.0,-3.311343246928389e-05
pf_interval,PF infinite,ga,0.18421043445100882,0,0.0,0.0
pf_interval,PF infinite,random,0.5334495006889114,0,0.0,0.0
pf_interval,PF ≥ 1.50,ga,1.2238595889183164,11,-0.02100458103984068,-0.0004239658549325398
pf_interval,PF ≥ 1.50,random,1.3399438696614987,10,0.0,0.0
trades_interval,0–24,ga,0.7031055605754699,0,0.0,0.0
trades_interval,0–24,random,0.7132819807362828,0,0.0,0.0
trades_interval,100–149,ga,1.2435043187239998,7,-0.10950758455015813,-0.012128606902640282
trades_interval,100–149,random,1.1438613157387572,12,-0.06455129770053689,-0.0067533134405726725
trades_interval,150–199,ga,1.0429204015339706,7,-0.10746897078450529,-0.01699543571684864
trades_interval,150–199,random,0.9438005707255572,6,-0.07000211217236868,-0.009848572088552443
trades_interval,200–250,ga,0.790565918720694,4,-0.09933204360501646,-0.020095711444305997
trades_interval,200–250,random,0.7412119841495588,4,-0.0746371426168406,-0.014142917415788353
trades_interval,25–49,ga,1.4753902799101795,12,-0.10804480089275699,-0.0040720750138959205
trades_interval,25–49,random,1.5975003348195174,12,-0.06463748961610682,-0.0020226051218328878
trades_interval,50–74,ga,1.4562388196521598,12,-0.08640302948700379,-0.005255986656303169
trades_interval,50–74,random,1.4302716918606326,12,-0.06063318440374563,-0.0032311254898219344


Los mapas completos, lifts por generación, consistencia mensual, interacciones y diccionario están en `reports/p13b_artifacts/`.

## Hipótesis descriptivas candidatas (no filtros)

1. PF histórico 1.30–<1.50 presenta enriquecimiento E en ambos métodos y en los 12 meses, pero la expectancy neta mediana permanece negativa; se falsaría si desaparece al replicar en generaciones cronológicamente posteriores.
2. Los intervalos de 25–74 operaciones históricas muestran lifts E elevados en ambos métodos, pero pueden reflejar composición/actividad y no margen económico; se falsaría si el efecto no persiste tras emparejar actividad.
3. Los cuantiles bajos de MaxDD histórico muestran enriquecimiento descriptivo en varios estratos, con dependencia de método y condición de actividad; se falsaría si cambia de signo en una muestra temporal no solapada.

## Control de carteras

No ejecutado: no existen ledgers completos por estrategia para construir estratos arbitrarios con el motor operativo. No se sumaron retornos individuales ni se presentó una aproximación como cartera.

## Conclusión

Existe enriquecimiento descriptivo de P(E) en algunos intervalos históricos, especialmente PF intermedio, pero no evidencia de predictibilidad histórica económicamente utilizable: la expectancy neta agregada sigue siendo negativa y no hay control de carteras. `NO HISTORICAL PREDICTABILITY EVIDENCE` como política operativa validada.

## Limitaciones

Las estrategias están correlacionadas, las ventanas de entrenamiento se solapan durante cinco meses y los 12 meses no son réplicas independientes. Los subconjuntos condicionados por actividad son retrospectivos y no pueden ser predictores operativos.
