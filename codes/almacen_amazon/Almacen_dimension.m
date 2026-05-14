% =========================================================================
% CÁLCULOS INICIALES: DIMENSIONAMIENTO Y CAPACIDAD DEL ALMACÉN
% =========================================================================
clear; clc;

%% 1. ÁREAS Y SUPERFICIES
% Dimensiones generales del edificio
largo_total = 300; % metros
ancho_total = 150; % metros
area_total = largo_total * ancho_total;

% Dimensiones de la zona robotizada (Robotics Area)
largo_robotics = 210; % metros
ancho_robotics = 95;  % metros
area_robotics_exacta = largo_robotics * ancho_robotics; % 19.950 m2
area_robotics_aprox = 20000; % Redondeo asumido en el proyecto para facilidad de cálculo

% Dimensiones de la estantería
largo_estanteria = 1.5; % metros
ancho_estanteria = 1.5; % metros
area_estanteria = largo_estanteria * ancho_estanteria; % 2.25 m2

%% 2. CÁLCULO DE ESTANTERÍAS POR PLANTA
pct_area_util = 0.50; % 50% de área útil (pasillos, zonas de carga, etc.)
area_util_planta = area_robotics_aprox * pct_area_util; % 10.000 m2

% Cálculo teórico de estanterías que caben
estanterias_teoricas = area_util_planta / area_estanteria; % 4444.4 estanterías

% Asignación final por diseño del proyecto
estanterias_por_planta = 5000; 

%% 3. CAPACIDAD POR ESTANTERÍA
% Huecos físicos
% Composición: 7x3x2 + 7x2 = 42 + 14 = 56
huecos_por_estanteria = (7 * 3 * 2) + (7 * 2); 
paquetes_por_hueco = 12;

% Capacidades de la estantería
cap_maxima_estanteria = huecos_por_estanteria * paquetes_por_hueco; % 672 paquetes
pct_ocupacion = 0.67; % Factor de utilización (67%)
cap_real_estanteria = cap_maxima_estanteria * pct_ocupacion; % 450.24 paquetes

%% 4. CAPACIDAD TOTAL DEL EDIFICIO Y REPARTO ABC
num_plantas = 3;

% Capacidad real total (manteniendo decimales para que cuadre exacto)
capacidad_planta = cap_real_estanteria * estanterias_por_planta; % 2.251.200 paquetes
capacidad_total = capacidad_planta * num_plantas; % 6.753.600 paquetes

% Porcentajes de diseño ABC
pct_A = 0.15;
pct_B = 0.15;
pct_C = 0.70;

% Reparto de inventario
paquetes_A = capacidad_total * pct_A;
paquetes_B = capacidad_total * pct_B;
paquetes_C = capacidad_total * pct_C;

%% 5. IMPRESIÓN DE RESULTADOS EN CONSOLA (FORMATO INFORME)
fprintf('======================================================\n');
fprintf('  RESUMEN DE DIMENSIONAMIENTO DEL CENTRO LOGÍSTICO\n');
fprintf('======================================================\n\n');

fprintf('--- 1. ÁREAS Y SUPERFICIES ---\n');
fprintf('Área total del edificio:      %.0f m2 (%dm x %dm)\n', area_total, largo_total, ancho_total);
fprintf('Área Robotics (por planta):   %.0f m2 aprox.\n', area_robotics_aprox);
fprintf('Área de una estantería:       %.2f m2 (%g x %g m)\n', area_estanteria, largo_estanteria, ancho_estanteria);
fprintf('Área útil asumida (50%%):      %.0f m2\n\n', area_util_planta);

fprintf('--- 2. DIMENSIONAMIENTO DE ESTANTERÍAS ---\n');
fprintf('Estanterías teóricas (calc.): %.0f estanterías\n', estanterias_teoricas);
fprintf('Estanterías de DISEÑO:        %.0f estanterías/planta\n\n', estanterias_por_planta);

fprintf('--- 3. CAPACIDAD POR ESTANTERÍA ---\n');
fprintf('Huecos físicos:               %d huecos/estantería\n', huecos_por_estanteria);
fprintf('Capacidad teórica por hueco:  %d paquetes\n', paquetes_por_hueco);
fprintf('Capacidad máxima estantería:  %d paquetes\n', cap_maxima_estanteria);
fprintf('Capacidad real (67%% ocup.):   %.2f paquetes (Aprox 450)\n\n', cap_real_estanteria);

fprintf('--- 4. CAPACIDAD TOTAL (3 PLANTAS) ---\n');
fprintf('Capacidad de 1 Planta:        %.0f paquetes\n', capacidad_planta);
fprintf('CAPACIDAD TOTAL (3 Plantas):  %.0f paquetes\n\n', capacidad_total);

fprintf('--- 5. REPARTO DE INVENTARIO (ZONIFICACIÓN ABC) ---\n');
fprintf('Productos tipo A (15%%):       %.0f paquetes\n', paquetes_A);
fprintf('Productos tipo B (15%%):       %.0f paquetes\n', paquetes_B);
fprintf('Productos tipo C (70%%):       %.0f paquetes\n', paquetes_C);
fprintf('======================================================\n');