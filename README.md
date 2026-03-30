# Challenge Assignment

This program automates the full data preparation and analysis workflow for the economic indicators used in the project. It connects to the FRED database using an API key and downloads the required time series, including inflation, GDP, unemployment, interest rates, and expected inflation. The program then organizes the data into a consistent structure, converting monthly series into quarterly values so that all variables can be analyzed together.

After the data is aligned to the same quarterly frequency, the program merges the datasets into one combined file. Additional calculated fields are created, such as lagged interest rates and economic gaps, which are commonly used in macroeconomic analysis. These calculated variables help capture relationships between economic conditions and policy decisions.

Finally, the program performs a rolling regression analysis to estimate how the Federal Funds Rate responds to changes in inflation, output, and unemployment over time. The results are saved into several output files with shorter, simplified names so they are easier to identify and use in other software such as Excel, Tableau, or Python visualization tools.

Overall, the program streamlines what would normally be multiple manual steps into a single automated workflow, improving consistency, reducing errors, and saving time when updating or expanding the analysis.