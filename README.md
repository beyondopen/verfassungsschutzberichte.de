# Verfassungsschutzberichte.de

## Development

```bash
  docker-compose up
```

## Production

Host it with Dokku. Link a postgres db and a redis cache. Then mount two folder for the static content:

- folder with pdfs to `/data/pdfs`
- folder with resulting images to `/data/imgs`

To serve the images and pdfs via nginx (xsendfile), adapt the nginx config.

```bash
location /x_images {
  internal;
  alias /folder/with/images;
}

location /x_pdfs {
  internal;
  alias /folder/with/pdfs;
}
```

## One-off commands

- clear cache: `dokku run the-app flask clear-cache`
- add documents: `dokku run the-app flask update-docs '*'`

## PDF preprocessing

All docouments should be in the A5 portrait format. Several helper scripts exists but manual work is unavoidable.

Two folders exists: raw, where all the original PDFs shoul be and 'cleaned', for all clean and normalized PDFs are. Often clean and raw are identical.

## Search

Default are wildcards

## License

MIT.
