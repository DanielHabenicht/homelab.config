# Mail Archiving

First start has to be interactive: 
1. Only start the mailarchiva in a seperate terminal `docker compose run --use-aliases -it mailarchiva`
2. Start proxy `docker compose run --use-aliases -it emailproxy python -m emailproxy --no-gui --config-file /config/emailproxy.config --external-auth`
3. Setup the connection inside mailarchiva as emailproxy:2993 unsecured. 


> Does not work as expected and deleted half my emails... instead of just backing them up.