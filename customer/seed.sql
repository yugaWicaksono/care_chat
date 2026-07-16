INSERT INTO customers (client_number, name, contact_info, address) VALUES
    ('12345', 'Jan Jansen', 'jan@example.test', 'Teststraat 1, Amsterdam'),
    ('12346', 'Marieke de Vries', 'marieke@example.test', 'Voorbeeldlaan 22, Utrecht'),
    ('12347', 'Pieter Bakker', 'pieter@example.test', 'Kerkstraat 5, Rotterdam')
ON CONFLICT (client_number) DO NOTHING;
