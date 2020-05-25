#helper functions for musmemfmri experiments


#function takes in face stim and assembles a bio
def assembleThisBio(thisStim,NotAPracticeTrial,params):
    bio = params['bio_template'][0]
    currBioDic, = {'picture': thisStim[0]} #use this dict later to log in db
    for iftr in params['bioFeature_names']:

        # get all the possible attributes 
        possibleAttributes = Attribute.objects.filter(attribute_class=iftr)
        #figure out gender of the chosen relation and limit names based on that
        if iftr in ['relation_name']:
            #the gender attribute id (parent) is linked to this in attr attr 
            relationAxA = AttributeXAttribute.objects.get(child=currBioDic['relation'])
            #relationAxA.parent #this is the gender
            import pdb; pdb.set_trace()

            #now find all names with that gender
            #not sure why this one won't work...
            possibleAttributes.filter(parents=relationAxA.parent)

            currAttribte = possibleAttributes[random.randrange(0,len(possibleAttributes))] #temporary

        if NotAPracticeTrial:
            #going to randomize based on previous subjects
            #need a function here !!!!!!
            print(f'Randomizing bio assignments based on previous participants.')
            currAttribte = possibleAttributes[1]
        else:
            print(f'Practice trial: previous bio assignments being ignored.')
            currAttribte = possibleAttributes[random.randrange(0,len(possibleAttributes))]

        currBioDic[iftr] = currAttribte #assign it for later entry in attrXattr

        # fill in the bio
        bio = bio.replace('[insert_'+iftr+']',currAttribte.name)

        return currBioDic, bio

# Create our attribute X attribute entries for a specific bio
def logThisBio(currBioDic,currTrialAttribute,params):
	#enter each feature for a pic; parent attrb is the current trial type/number
    for iftr in params['bioFeature_names']:
        mappingName = subject.name
        mappingValText = currBioDic['picture'].name
        childattr = currBioDic[iftr]
        parentattr = currTrialAttribute

        import pdb; pdb.set_trace()        
        #axa = AttributeXAttribute.objects.get_or_create(child=childattr, parent=parentattr,         
        #            mapping_value_text = mappingValText, mapping_name=mappingName)
        axa = 1

        #verify it was made
        #dbcurrBioDic, dbbio = doesThisBioExist(currBioDic['subject'],currTrialAttribute,params)
        success = True

    return axa, success
    

# Return the bioDic and bio text if trial already exists in attr X attr table
def doesThisBioExist(subject,currTrialAttribute,params):
	currTrialEntry = AttributeXAttribute.objects.filter(parent=currTrialAttribute, 
					mapping_name=subject.name)

	#build up the dictionary with all features
	bio = params['bio_template'][0]
	currBioDic, = {'picture': thisStim[0]} 
	for iftr in params['bioFeature_names']:
		mappingName = subject.name
		mappingValText = currBioDic['picture'].name
		childattr = currBioDic[iftr]
		parentattr = currTrialAttribute

	axa = AttributeXAttribute.objects.get(child=childattr, parent=parentattr, 
			mapping_value_text = mappingValText, mapping_name=mappingName)
	
	return currBioDic, bio





