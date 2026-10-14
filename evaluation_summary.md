# Charterloom AI Evaluation Summary

Projects: 2400. Training projects: 1920. Held out projects: 480 (235 high performing). Split: stratified by latent optimal workflow, whole projects held out.

## Workflow recommendation

<table>
<thead><tr><th>Model</th><th>Accuracy</th><th>Macro F1</th><th>Weighted F1</th><th>Top 2</th><th>Top 3</th><th>Log loss</th><th>ECE</th></tr></thead>
<tbody>
<tr><td>Charterloom blended</td><td>0.740</td><td>0.707</td><td>0.734</td><td>0.915</td><td>0.949</td><td>0.756</td><td>0.072</td></tr>
<tr><td>Semantic expert only</td><td>0.715</td><td>0.659</td><td>0.700</td><td>0.872</td><td>0.932</td><td>1.029</td><td>0.194</td></tr>
<tr><td>Structural expert only</td><td>0.719</td><td>0.696</td><td>0.718</td><td>0.902</td><td>0.945</td><td>0.831</td><td>0.102</td></tr>
<tr><td>Precedent expert only</td><td>0.694</td><td>0.654</td><td>0.688</td><td>0.872</td><td>0.923</td><td>0.972</td><td>0.154</td></tr>
<tr><td>Keyword rules baseline</td><td>0.536</td><td>0.544</td><td>0.542</td><td></td><td></td><td></td><td></td></tr>
<tr><td>Majority class baseline</td><td>0.238</td><td>0.048</td><td>0.092</td><td></td><td></td><td></td><td></td></tr>
</tbody>
</table>

## Per class results

<table>
<thead><tr><th>Workflow</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th></tr></thead>
<tbody>
<tr><td>Agile Scrum Product Delivery</td><td>0.716</td><td>0.857</td><td>0.780</td><td>56</td></tr>
<tr><td>Kanban Continuous Flow</td><td>0.700</td><td>0.778</td><td>0.737</td><td>27</td></tr>
<tr><td>Regulated Compliance Pipeline</td><td>0.591</td><td>0.500</td><td>0.542</td><td>26</td></tr>
<tr><td>Stage Gate Phased Delivery</td><td>0.839</td><td>0.743</td><td>0.788</td><td>35</td></tr>
<tr><td>Scaled Agile Release Train</td><td>0.947</td><td>1.000</td><td>0.973</td><td>18</td></tr>
<tr><td>Dual Track Discovery and Delivery</td><td>0.789</td><td>0.750</td><td>0.769</td><td>20</td></tr>
<tr><td>Scrumban Hybrid Flow</td><td>0.429</td><td>0.273</td><td>0.333</td><td>11</td></tr>
<tr><td>Change Controlled Operations</td><td>0.750</td><td>0.714</td><td>0.732</td><td>42</td></tr>
</tbody>
</table>

## Abstention and oracle agreement

<table>
<thead><tr><th>Measure</th><th>Value</th></tr></thead>
<tbody>
<tr><td>Review threshold</td><td>0.500</td></tr>
<tr><td>Coverage above threshold</td><td>0.843</td></tr>
<tr><td>Accuracy when confident</td><td>0.803</td></tr>
<tr><td>Accuracy when flagged for review</td><td>0.405</td></tr>
<tr><td>Recommender agreement with latent optimal workflow</td><td>0.800</td></tr>
<tr><td>Keyword rules agreement with latent optimal workflow</td><td>0.581</td></tr>
<tr><td>Historical human choice agreement with latent optimal</td><td>0.575</td></tr>
</tbody>
</table>

## Precedent retrieval

<table>
<thead><tr><th>Retriever</th><th>Precision at 5</th><th>Precision at 10</th><th>MRR</th><th>nDCG at 10</th></tr></thead>
<tbody>
<tr><td>Hybrid project space</td><td>0.281</td><td>0.268</td><td>0.493</td><td>0.276</td></tr>
<tr><td>Semantic embedding only</td><td>0.162</td><td>0.146</td><td>0.325</td><td>0.152</td></tr>
<tr><td>BM25 plus dense text RRF</td><td>0.169</td><td>0.163</td><td>0.328</td><td>0.164</td></tr>
</tbody>
</table>

## Adjustment selection

<table>
<thead><tr><th>Strategy</th><th>Precision</th><th>Recall</th><th>F1</th><th>Exact set match</th></tr></thead>
<tbody>
<tr><td>Charterloom evidence plus priors</td><td>0.739</td><td>0.810</td><td>0.773</td><td>0.273</td></tr>
<tr><td>Charter priors only</td><td>0.655</td><td>0.840</td><td>0.736</td><td>0.194</td></tr>
<tr><td>Post mortem evidence only</td><td>0.711</td><td>0.713</td><td>0.712</td><td>0.204</td></tr>
</tbody>
</table>

<table>
<thead><tr><th>Adjustment</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th></tr></thead>
<tbody>
<tr><td>Security review gate</td><td>0.904</td><td>0.893</td><td>0.898</td><td>242</td></tr>
<tr><td>Privacy impact assessment gate</td><td>0.763</td><td>0.965</td><td>0.852</td><td>197</td></tr>
<tr><td>User acceptance testing stage</td><td>0.611</td><td>0.805</td><td>0.695</td><td>41</td></tr>
<tr><td>Migration rehearsal stage</td><td>0.655</td><td>0.927</td><td>0.768</td><td>41</td></tr>
<tr><td>Accessibility review gate</td><td>0.963</td><td>0.906</td><td>0.933</td><td>85</td></tr>
<tr><td>Performance testing stage</td><td>0.718</td><td>0.699</td><td>0.708</td><td>73</td></tr>
<tr><td>Model validation gate</td><td>0.585</td><td>0.974</td><td>0.731</td><td>39</td></tr>
<tr><td>Vendor acceptance checkpoint</td><td>0.612</td><td>0.741</td><td>0.670</td><td>85</td></tr>
<tr><td>Cross team dependency synchronisation</td><td>0.667</td><td>0.972</td><td>0.791</td><td>72</td></tr>
<tr><td>Tighter WIP limits</td><td>0.505</td><td>0.449</td><td>0.475</td><td>107</td></tr>
<tr><td>Timeboxed research spikes</td><td>0.634</td><td>1.000</td><td>0.776</td><td>26</td></tr>
<tr><td>Mandatory rollback plan</td><td>0.853</td><td>0.776</td><td>0.812</td><td>134</td></tr>
<tr><td>Feature flag release control</td><td>0.720</td><td>0.643</td><td>0.679</td><td>28</td></tr>
<tr><td>Definition of ready guard</td><td>0.463</td><td>0.528</td><td>0.493</td><td>36</td></tr>
<tr><td>Stakeholder demonstration ceremony</td><td>0.810</td><td>0.660</td><td>0.727</td><td>97</td></tr>
</tbody>
</table>

## Generated configurations

<table>
<thead><tr><th>Measure</th><th>Value</th></tr></thead>
<tbody>
<tr><td>Configurations generated</td><td>480</td></tr>
<tr><td>Valid rate</td><td>1.000</td></tr>
<tr><td>Warnings total</td><td>7</td></tr>
<tr><td>Mean gates added</td><td>1.915</td></tr>
<tr><td>Mean automations added</td><td>1.177</td></tr>
<tr><td>Flagged for review rate</td><td>0.156</td></tr>
<tr><td>Latency ms p50</td><td>83.400</td></tr>
<tr><td>Latency ms p95</td><td>136.100</td></tr>
</tbody>
</table>
