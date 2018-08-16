#!/bin/bash
zip -r build.zip ./ -x ".git/*" -x ".idea/*" -x "*.iml" -x "out/*" -x "target/*" -x "lib/*"
