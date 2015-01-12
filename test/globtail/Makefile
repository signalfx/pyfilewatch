test:
	@i=1; while [ -x "test$${i}.sh" ]; do \
		printf "test$${i}:" ; \
		./test$${i}.sh || exit 1 ; \
		printf " PASS\n" ; \
		i=$$(($$i+1)) ; \
	done
