SELECT 'CREATE DATABASE myface_test' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'myface_test')\gexec
