#jinja_string = """<title>{{title}}</title>
# <ul>
# {% for section in output_sections %}
#     {% set ptg = (section['RAM-MEMORY']  / ram_used_memory) * 100 %}
#   <li>SECTION: {{ section['OUTPUT-SECTION'] }} RAM-USED: {{ section['RAM-MEMORY'] }}  PERCENTAGE-USED: {{'%0.2f' % ptg|float}}% </li>
# {% endfor %}
# </ul>"""

jinja_string = """
<!DOCTYPE html>
<html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            .collapsible {
              background-color: #777;
              color: white;
              cursor: pointer;
              padding: 18px;
              width: 100%;
              border: none;
              text-align: left;
              outline: none;
              font-size: 15px;
            }

            .active, .collapsible:hover {
              background-color: #555;
            }

            .content {
              padding: 0 18px;
              display: none;
              overflow: hidden;
              background-color: #f1f1f1;
            }
        </style>
    </head>
    <body>
        <h2>METRICS-GENERATOR</h2>        
        <p>ROM:</p>
        <button type="button" class="collapsible">Level 1</button>
        <div class="content">
            <p>
                {% for section in output_sections %}
                    {% set ptg = (section['ROM-MEMORY']  / rom_used_memory) * 100 %}
                    <li>SECTION: {{ section['OUTPUT-SECTION'] }} ROM-USED: {{ section['ROM-MEMORY'] }}  PERCENTAGE-USED: {{'%0.2f' % ptg|float}}% </li>
                {% endfor %}
            </p>
        </div>
        <button type="button" class="collapsible">Level 3</button>
        <div class="content">
            <p></p>
        </div>
        <button type="button" class="collapsible">Level 5</button>
        <div class="content">
            <p></p>
        </div>

        <p>RAM:</p>
        <button type="button" class="collapsible">Level 1</button>
        <div class="content">
            <p>
                {% for section in output_sections %}
                    {% set ptg = (section['RAM-MEMORY']  / ram_used_memory) * 100 %}
                    <li>SECTION: {{ section['OUTPUT-SECTION'] }} RAM-USED: {{ section['RAM-MEMORY'] }}  PERCENTAGE-USED: {{'%0.2f' % ptg|float}}% </li>
                {% endfor %}
            </p>
        </div>
        <button type="button" class="collapsible">Level 3</button>
        <div class="content">
            <p></p>
        </div>
        <button type="button" class="collapsible">Level 5</button>
        <div class="content">
            <p></p>
        </div>
        
        
        <p>DATAFLASH:</p>
        <button type="button" class="collapsible">Level 2</button>
        <div class="content">
            <p>                
            </p>
        </div>
        
        <p>EEPROM:</p>
        <button type="button" class="collapsible">Level 1</button>
        <div class="content">
            <p>
                {% for data in data_eeprom %}                    
                    <li>BLOCK-NAME: {{ data['NAME'] }} BLOCK-SIZE: {{ data['CRC-SIZE'] }}  PERCENTAGE-USED: {{'%0.2f' % data['CRC-PERCENTAGE-USED']|float}}% </li>
                {% endfor %}
            </p>
        </div>
        <button type="button" class="collapsible">Level 2</button>
        <div class="content">
            <p>
                {% for profile in profile_blocks %}                    
                    <li>PROFILE-NAME: {{ profile['PROFILE'] }} NUMBER-OF-BLOCKS: {{ profile['NUMBER'] }} </li>
                {% endfor %}
            </p>
        </div>  
        
        <p>LEVEL0:</p>
        <button type="button" class="collapsible">ROM</button>
        <div class="content">
            <p>
                {% set max = max_rom|int(max_rom,16) %}
                {% set min = min_rom|int(min_rom,16) %}
                {% set size = max - min %}
                {% set ptg = (rom_used_memory / size) * 100 %}
                <li>START-ADDRESS: {{ min_rom }}</li> 
                <li>END-ADDRESS: {{max_rom }}  
                <li>SIZE: {{size}}</li> 
                <li>TOTAL-USED-SIZE: {{rom_used_memory}}</li> 
                <li>USED-PERCENTAGE: {{'%0.2f' % ptg|float}}% </li>
            </p>
        </div>
        <button type="button" class="collapsible">RAM</button>
        <div class="content">
            <p>
                {% set max = max_ram|int(max_ram,16) %}
                {% set min = min_ram|int(min_ram,16) %}
                {% set size = max - min %}
                {% set ptg = (ram_used_memory / size) * 100 %}
                <li>START-ADDRESS: {{ min_ram }}</li> 
                <li>END-ADDRESS: {{max_ram }}</li>
                <li>SIZE: {{size}}</li>
                <li>TOTAL-USED-SIZE: {{ram_used_memory}}</li> 
                <li>USED-PERCENTAGE: {{'%0.2f' % ptg|float}}%</li>
            </p>
        </div>
        <button type="button" class="collapsible">EEPROM</button>
        <div class="content">
            <p>
                {% set ptg = (eeprom_total_used_size / eep_total_size) * 100 %}
                <li>SIZE: {{eep_total_size}}</li>
                <li>TOTAL-USED-SIZE: {{eeprom_total_used_size}}</li>
                <li>USED-PERCENTAGE: {{'%0.2f' % ptg|float}}%</li> 
            </p>
        </div>  
        <button type="button" class="collapsible">DATAFLASH</button>
        <div class="content">
            <p>                
                {% set ptg = (DataflashUsed / total_dataflash ) * 100 %}
                <li>START-ADDRESS: {{ data_flash_start }}</li> 
                <li>END-ADDRESS: {{data_flash_end }}</li>
                <li>SIZE: {{total_dataflash}}</li>
                <li>TOTAL-USED-SIZE: {{DataflashUsed}}</li> 
                <li>USED-PERCENTAGE: {{'%0.2f' % ptg|float}}%</li>
            </p>
        </div>
        
        <script>
        var coll = document.getElementsByClassName("collapsible");
        var i;
        for (i = 0; i < coll.length; i++) {
              coll[i].addEventListener("click", function() {
                    this.classList.toggle("active");
                    var content = this.nextElementSibling;
                    if (content.style.display === "block") {
                        content.style.display = "none";
                    } else {
                        content.style.display = "block";
                    }
              });
        }
        </script>

    </body>
</html>
"""