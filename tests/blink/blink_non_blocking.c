/*****************************************************************************
    Copyright (C) 2015 OLogN Technologies AG
    
    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 2 as
    published by the Free Software Foundation.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
    
*****************************************************************************/

#include "blink_state.h"
#include "papi.h"
#include "blink.h"
#line 22 "blink.c"
#define HAPI_GPIO_VALUE_LOW 0
#define HAPI_GPIO_VALUE_HIGH 1
#define HAPI_GPIO_TYPE_OUTPUT 0

void hapi_gpio_init(uint16_t pin_num)
{
}
#line 27 "blink.c"
void hapi_gpio_set_mode(uint16_t pin_num, uint8_t mode)
{
}
uint8_t blink_plugin_handler_init(const void* plugin_config, void* plugin_state)
{
return PLUGIN_OK;
}

uint8_t blink_plugin_exec_init(const void* plugin_config, void* plugin_state)
{
*(uint8_t*)plugin_state = 0;
#line 37 "blink.c"
blink_plugin_config* pc = (blink_plugin_config*)plugin_config;
hapi_gpio_init(pc->pin_led);
hapi_gpio_set_mode(pc->pin_led, HAPI_GPIO_TYPE_OUTPUT);
return PLUGIN_OK;
}

uint8_t blink_plugin_handler(const void* plugin_config, void* plugin_persistent_state, void* plugin_state, ZEPTO_PARSER* command, MEMORY_HANDLE reply, waiting_for* wf, uint8_t first_byte)
{
blink_plugin_state* sa_state = (blink_plugin_state*)plugin_state;
waiting_for* sa_wf = wf;
blink_plugin_config* pc = (blink_plugin_config*)plugin_config;
switch(sa_state->sa_next) {
case 0: break;
case 1: goto label_1;
case 2: goto label_2;
default: ZEPTO_ASSERT(0);
}
#line 49 "blink.c"
sa_state->data = blink_plugin_parser_read(command);
sa_state->i = 0;
for(; (sa_state->i)<(sa_state->data).total_blinks;  (sa_state->i)++)
{
papi_write_digital_pin(pc->pin_led, HAPI_GPIO_VALUE_HIGH);
papi_wait_handler_add_wait_for_timeout(sa_wf, (sa_state->data).delay_ms);
sa_state->sa_next = 1;
return PLUGIN_WAITING;
label_1:if(papi_wait_handler_is_waiting_for_timeout(0, sa_wf))
{
return PLUGIN_WAITING;
}
#line 55 "blink.c"
papi_write_digital_pin(pc->pin_led, HAPI_GPIO_VALUE_LOW);
papi_wait_handler_add_wait_for_timeout(sa_wf, (sa_state->data).delay_ms);
sa_state->sa_next = 2;
return PLUGIN_WAITING;
label_2:if(papi_wait_handler_is_waiting_for_timeout(0, sa_wf))
{
return PLUGIN_WAITING;
}
}
#line 58 "blink.c"
papi_reply_write_byte(reply, (sa_state->i));
sa_state->sa_next = 0;
#line 59 "blink.c"
return PLUGIN_OK;
}
