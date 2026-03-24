# Contributing to Clara Odoo Connector

Thank you for your interest in contributing! This project is maintained by Clara and open to the community.

## Ways to Contribute

- **Bug reports** — Open a GitHub issue with steps to reproduce, your Odoo version, and relevant logs.
- **Feature requests** — Open an issue describing the use case and expected behavior.
- **Pull requests** — Bug fixes and improvements are welcome. For larger changes, open an issue first to discuss the approach.

## Development Setup

1. Fork and clone the repository.
2. Start the local environment:
   ```bash
   docker compose up -d
   ```
3. Access Odoo at `http://localhost:8069` and install the **Clara – Spend Management Integration** module.
4. Make your changes inside `clara_connector/`.
5. Restart Odoo and upgrade the module to pick up changes:
   ```bash
   docker compose exec odoo odoo -u clara_connector --stop-after-init
   docker compose up -d
   ```

## Guidelines

- **Odoo conventions** — Follow Odoo 17 development guidelines (model naming, XML IDs, security rules).
- **No credentials in code** — Never commit API keys, certificates, or secrets. All credentials are stored in the Odoo database via the Settings UI.
- **Backward compatibility** — If you add new fields or models, provide a migration path or at minimum document the breaking change.
- **Keep it focused** — This module's scope is the Clara ↔ Odoo integration. Features unrelated to Clara's API are out of scope.

## Pull Request Checklist

- [ ] Changes work on a clean Odoo 17 install
- [ ] New models/fields have ACL entries in `security/ir.model.access.csv`
- [ ] New UI elements follow the existing view patterns
- [ ] No hardcoded credentials or internal URLs

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
