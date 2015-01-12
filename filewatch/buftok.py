class BufferedTokenizer:
    def __init__(self, delimiter='\n', size_limit=None):
        self.delimiter = delimiter
        self.size_limit = size_limit
        self.input = []
        self.input_size = 0

    def extract(self, data):
        '''Extract takes an arbitrary string of input data and returns an array of
        tokenized entities, provided there were any available to extract. '''
        # Extract token-delimited entities from the input string with
        # the split command.  There's a bit of craftiness here with
        # the -1 parameter.  Normally split would behave no
        # differently regardless of if the token lies at the very end
        # of the input buffer or not (i.e. a literal edge case)
        # Specifying -1 forces split to return "" in this case,
        # meaning that the last entry in the list represents a new
        # segment of data where the token has not been encountered
        entities = data.split(self.delimiter, -1)

        # Check to see if the buffer has exceeded capacity, if we're
        # imposing a limit
        if self.size_limit:
            if self.input_size + len(entities[0]) > self.input_size:
                raise Exception('input buffer full')

        # Move the first entry in the resulting array into the input buffer.
        # It represents the last segment of a token-delimited entity unless
        # it's the only entry in the list.
        self.input.append(entities.pop(0))

        # If the resulting array from the split is empty, the token was not
        # encountered (not even at the end of the buffer).  Since we've
        # encountered no token-delimited entities this go-around, return
        # an empty array.
        if not entities:
            return []

        # At this point, we've hit a token, or potentially multiple tokens.
        # Now we can bring together all the data we've buffered from earlier
        # calls without hitting a token, and add it to our list of discovered
        # entities.
        entities.insert(0, ''.join(self.input))

        # Now that we've hit a token, joined the input buffer and added it to
        # the entities list, we can go ahead and clear the input buffer.  All
        # of the segments that were stored before the join can now be garbage
        # collected.
        self.input = []

        # The last entity in the list is not token delimited, however, thanks
        # to the -1 passed to split.  It represents the beginning of a new
        # list of as-yet-untokenized data, so we add it to the start of the
        # list.
        self.input.append(entities.pop())

        # Set the new input buffer size, provided we're keeping track
        if self.size_limit:
            self.input_size = len(self.input.first)

        # Now we're left with the list of extracted token-delimited entities we
        # wanted in the first place.  Hooray!
        return entities

    def flush(self):
        '''Flush the contents of the input buffer, i.e. return the input buffer
        even though a token has not yet been encountered'''
        buffer = ''.join(self.input)
        self.input = []
        if self.size_limit:
            self.input_size = 0
        return buffer

    def empty(self):
        return len(self.input) == 0
