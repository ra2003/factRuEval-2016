# This module deals primarily with the standard markup representation

import os
import csv

from dialent.config import Config

from dialent.objects import Token
from dialent.objects import Span
from dialent.objects import Entity
from dialent.objects import Interval
from dialent.objects import TokenSet

#########################################################################################

class Standard:
    """Standard document data loaded from a set of export files.
    
    The set currently includes:
     - 'NAME.txt'
     - 'NAME.tokens'
     - 'NAME.spans'
     - 'NAME.objects'
     """
    
    def __init__(self, name, path='.'):
        try:
            full_name = os.path.join(path, name)
            self.loadTokens(full_name + '.tokens')
            self.loadSpans(full_name + '.spans')
            self.loadEntities(full_name + '.objects')
            self.loadText(full_name + '.txt')
        except Exception as e:
            print('Failed to load the standard of {}:'.format(name))
            print(e)
    
    def loadTokens(self, filename):
        """Load the data from a file with the provided name
        
        Raw token data should be loaded from one of the system export '.tokens' file"""
        self.tokens = []
        
        with open(filename, 'r', encoding='utf-8') as f:
            rdr = csv.reader(f, delimiter=Config.DEFAULT_DELIMITER, quotechar=Config.QUOTECHAR)
            
            for index, line in enumerate(rdr):
                if len(line) == 0:
                    # skip the empty lines
                    continue
                
                if len(line) != Config.TOKEN_LINE_LENGTH:
                    # bad non-empty line
                    raise Exception(
                        'Wrong length in line {} of file {}'.format(
                            index, filename))
                
                self.tokens.append(
                    Token(*line) )

        # fill the token dictionary
        self._token_dict = dict([(x.id, x) for x in self.tokens])
        
        # set neighboor links in tokens
        self.tokens = sorted(self.tokens, key=lambda x: x.start)
        for i, token in enumerate(self.tokens):
            if i != 0:
                token.prev = self.tokens[i-1]
            if i != len(self.tokens)-1:
                token.next = self.tokens[i+1]

                
    def loadSpans(self, filename):
        """Load the data from a file with the provided name
        
        Raw span data should be loaded from one of the system export '.spans' file
        
        Expected format:
        line = <left> SPAN_FILE_SEPARATOR <right>
        left = <span_id> <tag_name> <start_pos> <nchars> <start_token> <ntokens>
        right ::= [ <token>]+ [ <token_text>]+     // <ntokens> of each
            """
        self.spans = []
        
        with open(filename, 'r', encoding='utf-8') as f:
            for index, line in enumerate(f):
                if len(line) == 0:
                    # skip the empty lines
                    continue
                
                parts = line.split(Config.SPAN_FILE_SEPARATOR)
                if len(parts) != 2:
                    # bad non-empty line
                    raise Exception(
                        'Expected symbol "{}" missing in line {} of file {}'.format(
                            Config.SPAN_FILE_SEPARATOR, index, filename))
                    
                left = parts[0]
                right = parts[1]
                
                filtered_left = [i
                     for i in left.split(Config.DEFAULT_DELIMITER)
                         if len(i) > 0]
                
                if len(filtered_left) < 6:
                    raise Exception(
                        'Missing left parts in line {} of file {}'.format(
                            index, filename))
                    
                new_span = Span(*filtered_left)
                
                filtered_right = [i
                      for i in right.split(Config.DEFAULT_DELIMITER)
                            if len(i) > 0]
                if len(filtered_right) != 2*new_span.ntokens:
                    raise Exception(
                        'Missing right parts in line {} of file {}'.format(
                            index, filename))
                
                
                token_ids = [int(x) for x in filtered_right[:new_span.ntokens]]
                new_span.tokens = [self._token_dict[x] for x in token_ids]
                new_span.text = ' '.join(filtered_right[new_span.ntokens:])
                new_span.text = new_span.text.replace('\n', '')
                
                self.spans.append(new_span)
                
        # fill the span dictionary
        self._span_dict = dict([(x.id, x) for x in self.spans])

    def loadEntities(self, filename):
        """Load the data from a given 'objects' file. Expected format:
        
        line = <object_id> <type> <span_id>
        """
        
        self.entities = []
        with open(filename) as f:
            r = csv.reader(f, delimiter=' ', quotechar=Config.QUOTECHAR)
            for index, line in enumerate(r):
                if len(line) == 0:
                    continue
                
                if len(line) <= 2:
                    raise Exception(
                        'Missing spans in object description: line {} of file {}'.format(
                            index, filename))
                
                try:
                    entity_id = int(line[0])
                    span_indices = [int(descr) for descr in line[2:]]
                except Exception as e:
                    raise Exception('Invalid entity or span id: line {} of file {}:\n{}'.format(
                        index, filename, e))
                self.entities.append(
                    Entity(entity_id, line[1], span_indices, self._span_dict))
                
    def loadText(self, filename):
        """Load text from the associated text file"""
        with open(filename, 'r', encoding='utf-8') as f:
            self.text = ''.join( [line for line in f] )
            
    def makeTokenSets(self, is_locorg_allowed=True):
        """Create a dictionary of typed TokenSet objects corresponding to the entities
        
        is_locorg_allowed - enable/disable 'LocOrg' tag"""
        
        # determine what tags are allowed
        allowed_tags = set(['org', 'per', 'loc'])
        if is_locorg_allowed:
            allowed_tags.add('locorg')
            
        res = dict([(x, []) for x in allowed_tags])
        for entity in self.entities:
            key = entity.tag
            if key == 'locorg' and not is_locorg_allowed:
                key = 'loc'
            assert(key in allowed_tags)
            ts = TokenSet(
                    [x for span in entity.spans for x in span.tokens],
                    key)
            for span in entity.spans:
                for token in span.tokens:
                    ts.setMark(token, span.tag)
            res[key].append(ts)
        return res